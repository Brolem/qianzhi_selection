"""Build grid-level scoring indicators from Step 6 POI counts."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import get_path, load_config


GRID_FIELDS = [
    "grid_id",
    "district_name",
    "adcode",
    "centroid_lon",
    "centroid_lat",
    "area_km2",
    "data_source",
]
COUNT_FIELDS = [
    "convenience_store_count",
    "supermarket_count",
    "restaurant_count",
    "fast_food_count",
    "snack_count",
    "cafe_count",
    "tea_count",
    "school_count",
    "hospital_count",
    "mall_count",
    "office_count",
    "residential_count",
    "bus_stop_count",
    "subway_station_count",
    "parking_count",
]
AUDIT_FIELDS = [
    "poi_total_count",
    "poi_category_coverage",
    "has_poi_activity",
]
METRIC_COMPONENTS = {
    "traffic_accessibility": [
        "bus_stop_count",
        "subway_station_count",
        "parking_count",
    ],
    "consumption_potential": [
        "residential_count",
        "supermarket_count",
        "mall_count",
        "school_count",
        "hospital_count",
    ],
    "employment_customer_proxy": [
        "office_count",
        "mall_count",
        "school_count",
        "restaurant_count",
    ],
    "business_atmosphere": [
        "mall_count",
        "restaurant_count",
        "cafe_count",
        "tea_count",
        "supermarket_count",
    ],
    "convenience_synergy_score": [
        "residential_count",
        "school_count",
        "hospital_count",
        "bus_stop_count",
        "supermarket_count",
    ],
    "light_food_synergy_score": [
        "office_count",
        "school_count",
        "mall_count",
        "bus_stop_count",
        "cafe_count",
        "tea_count",
    ],
    "convenience_competition_pressure": [
        "convenience_store_count",
        "supermarket_count",
    ],
    "light_food_competition_pressure": [
        "restaurant_count",
        "fast_food_count",
        "snack_count",
        "cafe_count",
        "tea_count",
    ],
}
METRIC_FIELDS = list(METRIC_COMPONENTS)
OUTPUT_FIELDS = GRID_FIELDS + COUNT_FIELDS + AUDIT_FIELDS + METRIC_FIELDS


def log_minmax(series: pd.Series) -> pd.Series:
    """Apply log1p and global Min-Max scaling to the 0-100 range."""
    values = pd.to_numeric(series, errors="raise").astype(float)
    transformed = np.log1p(values)
    minimum = float(transformed.min())
    maximum = float(transformed.max())
    if maximum == minimum:
        return pd.Series(0.0, index=series.index, dtype=float)
    return ((transformed - minimum) / (maximum - minimum) * 100.0).astype(float)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [field for field in required if field not in frame.columns]
    if missing:
        raise ValueError(f"{label}缺少字段：{', '.join(missing)}")


def _validate_unique_grids(frame: pd.DataFrame, label: str) -> None:
    duplicates = sorted(
        frame.loc[frame["grid_id"].duplicated(keep=False), "grid_id"]
        .astype(str)
        .unique()
        .tolist()
    )
    if duplicates:
        raise ValueError(f"{label}存在重复网格：{', '.join(duplicates)}")


def _clean_counts(counts: pd.DataFrame) -> pd.DataFrame:
    result = counts.copy()
    for field in COUNT_FIELDS:
        original = result[field]
        numeric = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & numeric.isna()
        if invalid.any():
            raise ValueError(f"{field} 必须为数字")
        numeric = numeric.fillna(0)
        if numeric.lt(0).any():
            raise ValueError(f"{field} 不能为负数")
        result[field] = numeric
    return result


def build_grid_scoring_input(
    counts: pd.DataFrame,
    grids: pd.DataFrame,
) -> pd.DataFrame:
    """Join sampled grids with counts and construct normalized indicators."""
    _require_columns(
        counts,
        ["grid_id", "district_name", *COUNT_FIELDS],
        "POI 统计",
    )
    _require_columns(grids, GRID_FIELDS, "评价网格")
    _validate_unique_grids(counts, "POI 统计")
    _validate_unique_grids(grids, "评价网格")

    clean_counts = _clean_counts(counts)
    grid_values = grids[GRID_FIELDS].copy()
    grid_values = grid_values.rename(columns={"district_name": "grid_district_name"})
    merged = clean_counts.merge(
        grid_values,
        on="grid_id",
        how="left",
        validate="one_to_one",
        sort=False,
    )

    missing_grid = merged["grid_district_name"].isna()
    if missing_grid.any():
        missing_ids = merged.loc[missing_grid, "grid_id"].astype(str).tolist()
        raise ValueError(f"POI 统计网格缺少空间信息：{', '.join(missing_ids)}")

    district_mismatch = (
        merged["district_name"].astype(str)
        != merged["grid_district_name"].astype(str)
    )
    if district_mismatch.any():
        mismatch_ids = merged.loc[district_mismatch, "grid_id"].astype(str).tolist()
        raise ValueError(f"POI 统计与评价网格区县不一致：{', '.join(mismatch_ids)}")

    merged = merged.drop(columns=["grid_district_name"])
    normalized = {
        field: log_minmax(merged[field])
        for field in COUNT_FIELDS
    }
    for metric, components in METRIC_COMPONENTS.items():
        merged[metric] = (
            pd.concat([normalized[field] for field in components], axis=1)
            .mean(axis=1)
            .round(6)
        )

    merged["poi_total_count"] = merged[COUNT_FIELDS].sum(axis=1)
    merged["poi_category_coverage"] = merged[COUNT_FIELDS].gt(0).sum(axis=1)
    merged["has_poi_activity"] = merged["poi_total_count"].gt(0)

    for field in METRIC_FIELDS:
        if merged[field].isna().any() or not merged[field].between(0, 100).all():
            raise ValueError(f"指标 {field} 必须为 0-100 且不能包含空值")

    return merged[OUTPUT_FIELDS].copy()


def validate_output_scope(
    scoring_input: pd.DataFrame,
    expected_districts: list[str],
    grids_per_district: int,
) -> None:
    """Validate the formal Step 7 sample scope."""
    expected_total = len(expected_districts) * grids_per_district
    if len(scoring_input) != expected_total:
        raise ValueError(
            f"评分输入应为 {expected_total} 行，实际为 {len(scoring_input)} 行"
        )
    _validate_unique_grids(scoring_input, "评分输入")

    actual_districts = set(scoring_input["district_name"].astype(str))
    expected_set = {str(value) for value in expected_districts}
    if actual_districts != expected_set:
        raise ValueError(
            "评分输入区县集合不一致："
            f"应为 {', '.join(expected_districts)}；"
            f"实际为 {', '.join(sorted(actual_districts))}"
        )

    counts = scoring_input.groupby("district_name").size().to_dict()
    invalid = {
        district: int(counts.get(district, 0))
        for district in expected_districts
        if int(counts.get(district, 0)) != grids_per_district
    }
    if invalid:
        details = "，".join(
            f"{district}={count}" for district, count in invalid.items()
        )
        raise ValueError(
            f"每个区县应有 {grids_per_district} 行，实际为：{details}"
        )


def build_feature_engineering_report(
    scoring_input: pd.DataFrame,
    total_spatial_grid_count: int,
) -> str:
    """Build the Step 7 method and data-boundary report."""
    sample_count = len(scoring_input)
    zero_count = int((~scoring_input["has_poi_activity"]).sum())
    lines = [
        "# 网格级指标工程报告",
        "",
        "## 执行范围",
        "",
        f"- 本次评分输入：{sample_count} 个已采集 POI 的样本网格。",
        f"- 空间网格底表：{total_spatial_grid_count} 个空间网格。",
        "- 正式执行范围为 60 个样本网格，不为未采集 POI 的空间网格补零。",
        f"- 全零网格：{zero_count} 个，保留并标记为 `has_poi_activity=False`。",
        "",
        "## 归一化方法",
        "",
        "每个 POI 计数字段先将空值填 0，校验为非负数字，再执行 `log1p`，",
        "然后在全部样本网格范围内执行全局 Min-Max 归一化到 0-100。",
        "常量字段统一归零。复合指标对组成字段的归一化结果等权平均。",
        "不按区县分别归一化，保证三个区县之间可以直接比较。",
        "",
        "## 指标构造",
        "",
        "| 指标字段 | 组成计数字段 |",
        "| --- | --- |",
    ]
    for metric, components in METRIC_COMPONENTS.items():
        lines.append(f"| `{metric}` | {', '.join(f'`{item}`' for item in components)} |")

    lines.extend(
        [
            "",
            "## 数据与解释边界",
            "",
            "- Step 7 使用 Step 6 的统一关键词查询结果，只支持同一查询口径下的相对评价。",
            "- `poi_total_count` 是 15 类计数之和，不是跨类别去重后的唯一 POI 数量。",
            "- POI 类别之间允许交叉，指标不代表区域真实、完整的设施总量。",
            "- 全零网格保留用于审计，Step 8 必须将其排除出推荐榜单。",
            "- Step 6 使用统一 500 米周边查询半径，因此不按裁剪后的 `area_km2` 计算密度。",
            "- 官方宏观和就业数据位于 `data/processed/official/`，只作背景说明，",
            "  不参与网格指标计算，也不是本脚本运行的强依赖。",
            "",
            "## 指标分布",
            "",
            "| 指标字段 | 最小值 | 中位数 | 最大值 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for metric in METRIC_FIELDS:
        lines.append(
            f"| `{metric}` | {scoring_input[metric].min():.2f} | "
            f"{scoring_input[metric].median():.2f} | "
            f"{scoring_input[metric].max():.2f} |"
        )
    return "\n".join(lines) + "\n"


def _write_temp_text(target: Path, content: str, encoding: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        newline="",
        delete=False,
        dir=target.parent,
        suffix=".tmp",
    ) as file:
        file.write(content)
        return Path(file.name)


def write_outputs_atomically(
    scoring_input: pd.DataFrame,
    report: str,
    output_path: str | Path,
    report_path: str | Path,
) -> dict[str, Path]:
    """Write both formal outputs from complete temporary files."""
    scoring_target = Path(output_path)
    report_target = Path(report_path)
    scoring_csv = scoring_input.to_csv(index=False, encoding="utf-8-sig")
    scoring_temp = _write_temp_text(scoring_target, scoring_csv, "utf-8-sig")
    report_temp = _write_temp_text(report_target, report, "utf-8")
    previous_content = {
        scoring_target: scoring_target.read_bytes() if scoring_target.exists() else None,
        report_target: report_target.read_bytes() if report_target.exists() else None,
    }
    try:
        os.replace(scoring_temp, scoring_target)
        os.replace(report_temp, report_target)
    except Exception:
        for target, content in previous_content.items():
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    finally:
        scoring_temp.unlink(missing_ok=True)
        report_temp.unlink(missing_ok=True)
    return {"scoring": scoring_target, "report": report_target}


def run_feature_engineering(
    counts_path: str | Path,
    grids_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    expected_districts: list[str],
    grids_per_district: int,
    total_spatial_grid_count: int | None = None,
) -> dict[str, Path]:
    """Run Step 7 from explicit input and output paths."""
    counts_file = Path(counts_path)
    grids_file = Path(grids_path)
    if not counts_file.exists():
        raise FileNotFoundError(f"POI 统计文件不存在：{counts_file}")
    if not grids_file.exists():
        raise FileNotFoundError(f"评价网格文件不存在：{grids_file}")

    counts = pd.read_csv(counts_file)
    grids = pd.read_csv(grids_file, dtype={"adcode": str})
    scoring_input = build_grid_scoring_input(counts, grids)
    validate_output_scope(scoring_input, expected_districts, grids_per_district)
    if set(scoring_input["grid_id"].astype(str)) != set(counts["grid_id"].astype(str)):
        raise ValueError("评分输入与 POI 统计的网格集合不一致")

    spatial_count = total_spatial_grid_count
    if spatial_count is None:
        spatial_count = len(grids)
    report = build_feature_engineering_report(scoring_input, spatial_count)
    return write_outputs_atomically(
        scoring_input,
        report,
        output_path,
        report_path,
    )


def main() -> None:
    """Script entry point for Step 7."""
    cfg = load_config()
    processed_dir = get_path("processed_dir", cfg)
    results_dir = get_path("results_dir", cfg)
    outputs = run_feature_engineering(
        counts_path=processed_dir / "grid_poi_counts.csv",
        grids_path=processed_dir / "candidate_grids.csv",
        output_path=processed_dir / "grid_scoring_input.csv",
        report_path=results_dir / "feature_engineering_report.md",
        expected_districts=list(cfg["target_districts"]["first_version"]),
        grids_per_district=20,
    )
    scoring = pd.read_csv(outputs["scoring"])
    print(f"Grid scoring input: {outputs['scoring']}")
    print(f"Feature engineering report: {outputs['report']}")
    print(f"Scoring grids: {len(scoring)}")
    print(f"Zero-activity grids: {int((~scoring['has_poi_activity']).sum())}")


if __name__ == "__main__":
    main()
