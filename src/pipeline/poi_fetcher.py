"""Fetch and aggregate grid-level POI samples from Amap."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipeline.amap_client import AmapClient
from src.core.config import get_path, get_poi_categories, get_poi_typecodes, load_config


METRIC_CRS = "EPSG:32648"
GRID_CRS = "EPSG:4326"
RAW_FIELDS = [
    "grid_id",
    "district_name",
    "category_key",
    "category_keyword",
    "poi_id",
    "poi_name",
    "poi_type",
    "lon",
    "lat",
    "address",
    "source",
]
MAX_NETWORK_ATTEMPTS = 3
COMPARISON_FIELDS = [
    "grid_id",
    "district_name",
    "sample_group",
    "area_km2",
    "category_key",
    "category_keyword",
    "category_typecodes",
    "keyword_count",
    "typecode_count",
    "count_difference",
    "zero_to_nonzero",
]


def _require_grid_columns(grids: pd.DataFrame) -> None:
    required = {"grid_id", "district_name", "centroid_lon", "centroid_lat"}
    missing = sorted(required.difference(grids.columns))
    if missing:
        raise ValueError(f"评价网格缺少字段：{', '.join(missing)}")


def _select_district_grids(district_rows: pd.DataFrame, limit: int) -> pd.DataFrame:
    if limit <= 0:
        raise ValueError("grids_per_district 必须大于 0")
    if len(district_rows) <= limit:
        return district_rows.sort_values("grid_id").copy()

    points = gpd.GeoDataFrame(
        district_rows[["grid_id"]].copy(),
        geometry=gpd.points_from_xy(
            district_rows["centroid_lon"],
            district_rows["centroid_lat"],
        ),
        crs=GRID_CRS,
    ).to_crs(METRIC_CRS)
    points["x"] = points.geometry.x
    points["y"] = points.geometry.y
    center_x = float(points["x"].mean())
    center_y = float(points["y"].mean())
    points["center_distance"] = (
        (points["x"] - center_x) ** 2 + (points["y"] - center_y) ** 2
    )
    first_index = points.sort_values(
        ["center_distance", "grid_id"],
        kind="mergesort",
    ).index[0]

    selected_indices = [first_index]
    remaining = set(points.index).difference(selected_indices)
    while len(selected_indices) < limit:
        ranked: list[tuple[float, str, Any]] = []
        for index in remaining:
            x_value = float(points.at[index, "x"])
            y_value = float(points.at[index, "y"])
            min_distance = min(
                (x_value - float(points.at[selected, "x"])) ** 2
                + (y_value - float(points.at[selected, "y"])) ** 2
                for selected in selected_indices
            )
            ranked.append(
                (
                    min_distance,
                    str(points.at[index, "grid_id"]),
                    index,
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected_index = ranked[0][2]
        selected_indices.append(selected_index)
        remaining.remove(selected_index)

    selected = district_rows.loc[selected_indices].copy()
    selected["_selection_order"] = range(len(selected))
    return selected.sort_values("_selection_order").drop(columns="_selection_order")


def select_spatially_distributed_grids(
    grids: pd.DataFrame,
    grids_per_district: int,
) -> pd.DataFrame:
    """Select a stable, spatially distributed grid sample per district."""
    _require_grid_columns(grids)
    selected_parts = []
    district_order = grids["district_name"].astype(str).drop_duplicates().tolist()
    for district_name in district_order:
        district_rows = grids[grids["district_name"].astype(str).eq(district_name)]
        selected_parts.append(_select_district_grids(district_rows, grids_per_district))
    if not selected_parts:
        return grids.iloc[0:0].copy()
    return pd.concat(selected_parts, ignore_index=True)


def select_typecode_comparison_grids(
    grids: pd.DataFrame,
    existing_counts: pd.DataFrame,
    district_names: list[str],
) -> pd.DataFrame:
    """Select one largest zero grid and one median nonzero grid per district."""
    _require_grid_columns(grids)
    count_fields = [column for column in existing_counts.columns if column.endswith("_count")]
    if not count_fields:
        raise ValueError("现有 POI 统计缺少数量字段")

    counts = existing_counts.copy()
    counts["poi_total_count"] = counts[count_fields].fillna(0).sum(axis=1)
    merged = counts.merge(
        grids,
        on=["grid_id", "district_name"],
        how="left",
        validate="one_to_one",
    )
    if merged["area_km2"].isna().any():
        missing_ids = merged.loc[merged["area_km2"].isna(), "grid_id"].astype(str).tolist()
        raise ValueError(f"现有 POI 统计中的网格缺少空间信息：{', '.join(missing_ids)}")

    selected_rows = []
    for district_name in district_names:
        district = merged[merged["district_name"].astype(str).eq(str(district_name))].copy()
        zero_rows = district[district["poi_total_count"].eq(0)].sort_values(
            ["area_km2", "grid_id"],
            ascending=[False, True],
            kind="mergesort",
        )
        nonzero_rows = district[district["poi_total_count"].gt(0)].sort_values(
            ["poi_total_count", "grid_id"],
            kind="mergesort",
        )
        if zero_rows.empty:
            raise ValueError(f"{district_name} 缺少全零网格，无法执行分类编码对照")
        if nonzero_rows.empty:
            raise ValueError(f"{district_name} 缺少非零网格，无法执行分类编码对照")

        zero_row = zero_rows.iloc[0].copy()
        zero_row["sample_group"] = "zero"
        nonzero_row = nonzero_rows.iloc[len(nonzero_rows) // 2].copy()
        nonzero_row["sample_group"] = "nonzero"
        selected_rows.extend([zero_row, nonzero_row])

    return pd.DataFrame(selected_rows).reset_index(drop=True)


def _response_pois(response: dict[str, Any] | None) -> list[dict[str, Any]]:
    if response is None:
        raise RuntimeError("高德 API 无响应")
    if response.get("status") != "1":
        info = response.get("info")
        infocode = response.get("infocode")
        raise RuntimeError(f"高德 API 返回失败：info={info} infocode={infocode}")
    pois = response.get("pois", [])
    if not isinstance(pois, list):
        raise RuntimeError("高德 API 响应中的 pois 不是列表")
    return pois


def _request_poi_page(
    client: AmapClient,
    location: str,
    category_keyword: str | None,
    radius_m: int,
    city_name: str,
    page: int,
    page_size: int,
    category_typecodes: str | None = None,
) -> tuple[dict[str, Any], int]:
    for attempt in range(1, MAX_NETWORK_ATTEMPTS + 1):
        response = client.search_poi_around(
            location=location,
            keywords=None if category_typecodes else category_keyword,
            radius=radius_m,
            city=city_name,
            page=page,
            offset=page_size,
            types=category_typecodes,
        )
        if response is not None:
            return response, attempt
        if attempt < MAX_NETWORK_ATTEMPTS:
            time.sleep(attempt)
    raise RuntimeError(f"高德 API 连续 {MAX_NETWORK_ATTEMPTS} 次无响应")


def _text_value(value: Any) -> str:
    if value is None or value == []:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _parse_location(value: Any) -> tuple[float | str, float | str]:
    if not isinstance(value, str) or "," not in value:
        return "", ""
    lon_text, lat_text = value.split(",", maxsplit=1)
    try:
        return float(lon_text), float(lat_text)
    except ValueError:
        return "", ""


def fetch_grid_category(
    client: AmapClient,
    grid: pd.Series,
    category_key: str,
    category_keyword: str,
    city_name: str,
    radius_m: int,
    max_pages: int,
    page_size: int,
    category_typecodes: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Fetch one POI category for one grid with pagination and ID deduplication."""
    location = f"{float(grid['centroid_lon']):.8f},{float(grid['centroid_lat']):.8f}"
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    missing_location_count = 0
    request_count = 0

    for page in range(1, max_pages + 1):
        response, attempt_count = _request_poi_page(
            client,
            location,
            category_keyword,
            radius_m,
            city_name,
            page,
            page_size,
            category_typecodes,
        )
        request_count += attempt_count
        pois = _response_pois(response)
        for poi in pois:
            poi_id = _text_value(poi.get("id"))
            if poi_id and poi_id in seen_ids:
                continue
            if poi_id:
                seen_ids.add(poi_id)
            lon, lat = _parse_location(poi.get("location"))
            if lon == "" or lat == "":
                missing_location_count += 1
            rows.append(
                {
                    "grid_id": str(grid["grid_id"]),
                    "district_name": str(grid["district_name"]),
                    "category_key": category_key,
                    "category_keyword": category_keyword,
                    "poi_id": poi_id,
                    "poi_name": _text_value(poi.get("name")),
                    "poi_type": _text_value(poi.get("type")),
                    "lon": lon,
                    "lat": lat,
                    "address": _text_value(poi.get("address")),
                    "source": "amap_api_typecode" if category_typecodes else "amap_api",
                }
            )
        if len(pois) < page_size:
            break

    return rows, {
        "missing_location_count": missing_location_count,
        "request_count": request_count,
    }


def evaluate_typecode_comparison(
    comparison_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate whether the six-grid sample justifies a full typecode refetch."""
    frame = pd.DataFrame(comparison_rows)
    if frame.empty:
        raise ValueError("分类编码对照结果为空")

    grid_totals = frame.groupby(
        ["grid_id", "sample_group"],
        as_index=False,
    )[["keyword_count", "typecode_count"]].sum()
    zero_grids = grid_totals[grid_totals["sample_group"].eq("zero")]
    converted_zero_grid_count = int(
        (zero_grids["keyword_count"].eq(0) & zero_grids["typecode_count"].gt(0)).sum()
    )
    keyword_total = int(frame["keyword_count"].sum())
    typecode_total = int(frame["typecode_count"].sum())
    increase_ratio = (
        (typecode_total - keyword_total) / keyword_total
        if keyword_total > 0
        else (float("inf") if typecode_total > 0 else 0.0)
    )
    recommend = converted_zero_grid_count >= 1 or increase_ratio > 0.2
    return {
        "converted_zero_grid_count": converted_zero_grid_count,
        "keyword_total": keyword_total,
        "typecode_total": typecode_total,
        "increase_ratio": increase_ratio,
        "recommend_full_refetch": recommend,
    }


def _build_typecode_comparison_report(
    comparison_rows: list[dict[str, Any]],
    decision: dict[str, Any],
    request_count: int,
    radius_m: int,
    max_pages: int,
    page_size: int,
) -> str:
    frame = pd.DataFrame(comparison_rows)
    grid_summary = frame.groupby(
        ["grid_id", "district_name", "sample_group"],
        as_index=False,
    )[["keyword_count", "typecode_count"]].sum()
    category_summary = frame.groupby(
        ["category_key", "category_keyword", "category_typecodes"],
        as_index=False,
    )[["keyword_count", "typecode_count"]].sum()
    recommendation = "是" if decision["recommend_full_refetch"] else "否"
    ratio = decision["increase_ratio"]
    ratio_text = "无穷大" if ratio == float("inf") else f"{ratio * 100:.2f}%"

    lines = [
        "# POI 分类编码6网格核验报告",
        "",
        "- 样本网格数：6",
        "- 每个区县：1个全零网格、1个非零网格",
        f"- 查询半径：{radius_m} 米",
        f"- 每类最大页数：{max_pages}",
        f"- 每页数量：{page_size}",
        f"- 客户端查询调用次数（含缓存命中与重试）：{request_count}",
        "- 分类码表：高德官方 POI 分类编码，发布于2023年10月13日",
        "",
        "## 判定结果",
        "",
        f"- 全零网格转为非零数量：{decision['converted_zero_grid_count']}",
        f"- 关键词 POI 总数：{decision['keyword_total']}",
        f"- 分类编码 POI 总数：{decision['typecode_total']}",
        f"- 分类编码相对增幅：{ratio_text}",
        f"- 是否建议重新采集60个网格：{recommendation}",
        "",
        "判定规则：3个全零网格中至少1个转为非零，或6个网格的分类编码 POI 总数比关键词结果增加超过20%。",
        "",
        "## 网格对照",
        "",
        "| 区县 | 网格 | 样本类型 | 关键词总数 | 分类编码总数 |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in grid_summary.itertuples(index=False):
        lines.append(
            f"| {row.district_name} | {row.grid_id} | {row.sample_group} | "
            f"{int(row.keyword_count)} | {int(row.typecode_count)} |"
        )

    lines.extend(
        [
            "",
            "## 类别对照",
            "",
            "| 类别键 | 类别 | 分类编码 | 关键词总数 | 分类编码总数 |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in category_summary.itertuples(index=False):
        lines.append(
            f"| {row.category_key} | {row.category_keyword} | {row.category_typecodes} | "
            f"{int(row.keyword_count)} | {int(row.typecode_count)} |"
        )

    lines.extend(
        [
            "",
            "## 数据边界",
            "",
            "- 本报告只比较6个网格，不代表60个样本网格或全部评价网格。",
            "- 分类编码之间允许适度重叠，符合比赛级商业选址原型的验证范围。",
            "- 本次对照不修改现有关键词版明细、统计表和采集摘要。",
            "- 只有达到判定阈值，才另行制定60个网格重新采集计划。",
        ]
    )
    return "\n".join(lines) + "\n"


def run_typecode_comparison(
    client: AmapClient,
    selected_grids: pd.DataFrame,
    existing_counts: pd.DataFrame,
    category_keywords: dict[str, str],
    category_typecodes: dict[str, str],
    city_name: str,
    radius_m: int,
    max_pages: int,
    page_size: int,
    results_dir: str | Path,
) -> dict[str, Path]:
    """Run the independent six-grid typecode comparison and write its report."""
    if set(category_keywords) != set(category_typecodes):
        raise ValueError("poi_categories 与 poi_typecodes 的类别键必须完全一致")
    required_grid_fields = {"grid_id", "district_name", "area_km2", "sample_group"}
    missing_grid_fields = sorted(required_grid_fields.difference(selected_grids.columns))
    if missing_grid_fields:
        raise ValueError(f"分类编码样本网格缺少字段：{', '.join(missing_grid_fields)}")

    count_lookup = existing_counts.set_index("grid_id")
    comparison_rows: list[dict[str, Any]] = []
    request_count = 0
    for grid_number, (_, grid) in enumerate(selected_grids.iterrows(), start=1):
        grid_id = str(grid["grid_id"])
        if grid_id not in count_lookup.index:
            raise ValueError(f"现有 POI 统计缺少网格：{grid_id}")
        for category_key, category_keyword in category_keywords.items():
            count_field = f"{category_key}_count"
            if count_field not in existing_counts.columns:
                raise ValueError(f"现有 POI 统计缺少字段：{count_field}")
            typecodes = category_typecodes[category_key]
            rows, quality = fetch_grid_category(
                client=client,
                grid=grid,
                category_key=category_key,
                category_keyword=category_keyword,
                city_name=city_name,
                radius_m=radius_m,
                max_pages=max_pages,
                page_size=page_size,
                category_typecodes=typecodes,
            )
            request_count += quality["request_count"]
            keyword_count = int(count_lookup.at[grid_id, count_field])
            typecode_count = len(rows)
            comparison_rows.append(
                {
                    "grid_id": grid_id,
                    "district_name": str(grid["district_name"]),
                    "sample_group": str(grid["sample_group"]),
                    "area_km2": float(grid["area_km2"]),
                    "category_key": category_key,
                    "category_keyword": category_keyword,
                    "category_typecodes": typecodes,
                    "keyword_count": keyword_count,
                    "typecode_count": typecode_count,
                    "count_difference": typecode_count - keyword_count,
                    "zero_to_nonzero": keyword_count == 0 and typecode_count > 0,
                }
            )
        print(
            f"Typecode comparison progress: {grid_number}/{len(selected_grids)} "
            f"{grid['district_name']} {grid_id}"
        )

    decision = evaluate_typecode_comparison(comparison_rows)
    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "poi_typecode_comparison.csv"
    report_path = output_dir / "poi_typecode_comparison.md"
    report_text = _build_typecode_comparison_report(
        comparison_rows,
        decision,
        request_count,
        radius_m,
        max_pages,
        page_size,
    )

    with tempfile.TemporaryDirectory(prefix="poi_typecode_", dir=output_dir) as temp_dir:
        temp_path = Path(temp_dir)
        temp_csv = temp_path / csv_path.name
        temp_report = temp_path / report_path.name
        _write_csv(temp_csv, comparison_rows, COMPARISON_FIELDS)
        temp_report.write_text(report_text, encoding="utf-8")
        temp_csv.replace(csv_path)
        temp_report.replace(report_path)

    return {
        "csv": csv_path,
        "report": report_path,
        "recommend_full_refetch": decision["recommend_full_refetch"],
    }


def build_count_rows(
    grids: pd.DataFrame,
    raw_rows: list[dict[str, Any]],
    category_keywords: dict[str, str],
) -> list[dict[str, Any]]:
    """Aggregate raw POI rows into one count row per queried grid."""
    count_lookup: dict[tuple[str, str], int] = {}
    for row in raw_rows:
        key = (str(row["grid_id"]), str(row["category_key"]))
        count_lookup[key] = count_lookup.get(key, 0) + 1

    rows = []
    for grid in grids.itertuples(index=False):
        row: dict[str, Any] = {
            "grid_id": str(grid.grid_id),
            "district_name": str(grid.district_name),
        }
        for category_key in category_keywords:
            row[f"{category_key}_count"] = count_lookup.get(
                (str(grid.grid_id), category_key),
                0,
            )
        rows.append(row)
    return rows


def _write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_summary_report(summary: dict[str, Any]) -> str:
    lines = [
        "# 网格 POI 采集摘要",
        "",
        f"- 执行模式：{summary['mode']}",
        f"- 评价网格总数：{summary['total_grid_count']}",
        f"- 实际采集网格数：{summary['fetched_grid_count']}",
        f"- POI 类别数：{len(summary['category_keywords'])}",
        f"- 查询半径：{summary['radius_m']} 米",
        f"- 每类最大页数：{summary['max_pages']}",
        f"- 每页数量：{summary['page_size']}",
        f"- 客户端查询调用次数（含缓存命中与重试）：{summary['request_count']}",
        f"- 缺少坐标的 POI 数量：{summary['missing_location_count']}",
        "",
        "## 区县网格数",
        "",
    ]
    for district_name, count in summary["district_grid_counts"].items():
        lines.append(f"- {district_name}：{count}")

    lines.extend(["", "## 各类别 POI 数量", ""])
    for category_key, keyword in summary["category_keywords"].items():
        count = summary["category_counts"].get(category_key, 0)
        lines.append(f"- {category_key}（{keyword}）：{count}")

    lines.extend(
        [
            "",
            "## 数据边界",
            "",
            "- 本结果是已选网格的原型样本，不代表全部 POI。",
            "- 同一 POI 可能同时符合多个关键词，因此不同类别之间允许重叠。",
            "- 本次只统计实际完成 API 查询的网格，未查询网格不填充为零。",
            "- 高德 POI 数据用于原型验证，不用于真实客流、租金或盈利预测。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs_atomically(
    raw_rows: list[dict[str, Any]],
    count_rows: list[dict[str, Any]],
    output_dir: str | Path,
    report_path: str | Path,
    summary: dict[str, Any],
) -> dict[str, Path]:
    """Stage all Step 6 outputs, then replace the formal output files."""
    processed_path = Path(output_dir)
    final_report_path = Path(report_path)
    processed_path.mkdir(parents=True, exist_ok=True)
    final_report_path.parent.mkdir(parents=True, exist_ok=True)

    raw_path = processed_path / "grid_poi_raw.csv"
    counts_path = processed_path / "grid_poi_counts.csv"
    count_fields = ["grid_id", "district_name"] + [
        f"{key}_count" for key in summary["category_keywords"]
    ]

    with tempfile.TemporaryDirectory(
        prefix="poi_fetch_",
        dir=processed_path,
    ) as temp_dir:
        temp_path = Path(temp_dir)
        temp_raw = temp_path / raw_path.name
        temp_counts = temp_path / counts_path.name
        temp_report = temp_path / final_report_path.name
        _write_csv(temp_raw, raw_rows, RAW_FIELDS)
        _write_csv(temp_counts, count_rows, count_fields)
        temp_report.write_text(_build_summary_report(summary), encoding="utf-8")

        temp_raw.replace(raw_path)
        temp_counts.replace(counts_path)
        temp_report.replace(final_report_path)

    return {"raw": raw_path, "counts": counts_path, "report": final_report_path}


def run_api_fetch(
    client: AmapClient,
    grids: pd.DataFrame,
    category_keywords: dict[str, str],
    city_name: str,
    radius_m: int,
    max_pages: int,
    page_size: int,
    output_dir: str | Path,
    report_path: str | Path,
    total_grid_count: int,
) -> dict[str, Path]:
    """Fetch all selected grid/category pairs and write outputs on success."""
    raw_rows: list[dict[str, Any]] = []
    missing_location_count = 0
    request_count = 0

    for grid_number, (_, grid) in enumerate(grids.iterrows(), start=1):
        for category_key, category_keyword in category_keywords.items():
            rows, quality = fetch_grid_category(
                client=client,
                grid=grid,
                category_key=category_key,
                category_keyword=category_keyword,
                city_name=city_name,
                radius_m=radius_m,
                max_pages=max_pages,
                page_size=page_size,
            )
            raw_rows.extend(rows)
            missing_location_count += quality["missing_location_count"]
            request_count += quality["request_count"]
        print(
            f"POI progress: {grid_number}/{len(grids)} "
            f"{grid['district_name']} {grid['grid_id']}"
        )

    count_rows = build_count_rows(grids, raw_rows, category_keywords)
    category_counts = {key: 0 for key in category_keywords}
    for row in raw_rows:
        category_counts[str(row["category_key"])] += 1

    summary = {
        "total_grid_count": total_grid_count,
        "fetched_grid_count": len(grids),
        "district_grid_counts": grids.groupby("district_name").size().to_dict(),
        "category_counts": category_counts,
        "category_keywords": category_keywords,
        "max_pages": max_pages,
        "page_size": page_size,
        "radius_m": radius_m,
        "missing_location_count": missing_location_count,
        "request_count": request_count,
        "mode": "amap_api",
    }
    return write_outputs_atomically(
        raw_rows,
        count_rows,
        output_dir,
        report_path,
        summary,
    )


def load_demo_counts(demo_path: str | Path) -> pd.DataFrame:
    """Load the exact Step 6 demo count file or fail clearly."""
    path = Path(demo_path)
    if not path.exists():
        raise FileNotFoundError(f"demo POI 统计文件不存在：{path}")
    return pd.read_csv(path)


def _run_demo_mode(
    demo_path: Path,
    category_keywords: dict[str, str],
    output_dir: Path,
    report_path: Path,
) -> dict[str, Path]:
    demo_counts = load_demo_counts(demo_path)
    expected_fields = ["grid_id", "district_name"] + [
        f"{key}_count" for key in category_keywords
    ]
    missing = [field for field in expected_fields if field not in demo_counts.columns]
    if missing:
        raise ValueError(f"demo POI 统计文件缺少字段：{', '.join(missing)}")

    count_rows = demo_counts[expected_fields].to_dict("records")
    district_counts = demo_counts.groupby("district_name").size().to_dict()
    category_counts = {
        key: int(pd.to_numeric(demo_counts[f"{key}_count"], errors="coerce").fillna(0).sum())
        for key in category_keywords
    }
    summary = {
        "total_grid_count": len(demo_counts),
        "fetched_grid_count": len(demo_counts),
        "district_grid_counts": district_counts,
        "category_counts": category_counts,
        "category_keywords": category_keywords,
        "max_pages": 0,
        "page_size": 0,
        "radius_m": 0,
        "missing_location_count": 0,
        "request_count": 0,
        "mode": "demo",
    }
    return write_outputs_atomically(
        [],
        count_rows,
        output_dir,
        report_path,
        summary,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集并统计网格级高德 POI 样本")
    grid_group = parser.add_mutually_exclusive_group()
    grid_group.add_argument(
        "--grids-per-district",
        type=int,
        default=None,
        help="每个区县空间分散抽取的网格数，默认 20",
    )
    grid_group.add_argument(
        "--all-grids",
        action="store_true",
        help="采集输入文件中的全部网格",
    )
    parser.add_argument("--max-pages", type=int, default=2, help="每组查询最大页数，范围 1-8")
    parser.add_argument("--page-size", type=int, default=25, help="每页数量，范围 1-25")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.grids_per_district is not None and args.grids_per_district <= 0:
        raise ValueError("--grids-per-district 必须大于 0")
    if not 1 <= args.max_pages <= 8:
        raise ValueError("--max-pages 必须在 1 到 8 之间")
    if not 1 <= args.page_size <= 25:
        raise ValueError("--page-size 必须在 1 到 25 之间")


def main(argv: list[str] | None = None) -> None:
    """Script entry point for Step 6."""
    args = build_parser().parse_args(argv)
    _validate_args(args)
    cfg = load_config()
    processed_dir = get_path("processed_dir", cfg)
    results_dir = get_path("results_dir", cfg)
    grid_path = processed_dir / "candidate_grids.csv"
    if not grid_path.exists():
        raise FileNotFoundError(f"评价网格文件不存在：{grid_path}")

    grids = pd.read_csv(grid_path, dtype={"adcode": str})
    _require_grid_columns(grids)
    category_keywords = get_poi_categories(cfg)
    report_path = results_dir / "poi_fetch_summary.md"
    client = AmapClient()

    if not client.api_key:
        demo_path = get_path("demo_dir", cfg) / "grid_poi_counts_demo.csv"
        outputs = _run_demo_mode(
            demo_path,
            category_keywords,
            processed_dir,
            report_path,
        )
    else:
        if args.all_grids:
            selected_grids = grids.copy()
        else:
            per_district = args.grids_per_district or 20
            selected_grids = select_spatially_distributed_grids(grids, per_district)
        outputs = run_api_fetch(
            client=client,
            grids=selected_grids,
            category_keywords=category_keywords,
            city_name=str(cfg["project"]["city"]),
            radius_m=int(cfg["project"]["default_radius_m"]),
            max_pages=args.max_pages,
            page_size=args.page_size,
            output_dir=processed_dir,
            report_path=report_path,
            total_grid_count=len(grids),
        )

    print(f"grid POI raw: {outputs['raw']}")
    print(f"grid POI counts: {outputs['counts']}")
    print(f"POI fetch summary: {outputs['report']}")


if __name__ == "__main__":
    main()
