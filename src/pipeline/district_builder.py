"""Build target district metadata and boundary GeoJSON from Amap API."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipeline.amap_client import AmapClient
from src.core.config import get_path, load_config


DISTRICT_FIELDS = [
    "district_name",
    "city_name",
    "adcode",
    "center_lon",
    "center_lat",
    "has_boundary",
    "data_source",
]


def parse_center(center: str) -> tuple[float, float]:
    """Parse an Amap center string into longitude and latitude floats."""
    lon_text, lat_text = center.split(",", maxsplit=1)
    return float(lon_text), float(lat_text)


def parse_polyline(polyline: str) -> dict[str, Any]:
    """Parse an Amap district polyline string into GeoJSON geometry."""
    if not polyline:
        raise ValueError("缺少 polyline")

    polygons = []
    for part in polyline.split("|"):
        ring = []
        for pair in part.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            lon_text, lat_text = pair.split(",", maxsplit=1)
            ring.append([float(lon_text), float(lat_text)])
        if len(ring) < 3:
            raise ValueError("polyline 坐标点少于 3 个")
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        polygons.append([ring])

    if not polygons:
        raise ValueError("缺少有效 polyline 坐标")
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def select_district_item(response: dict[str, Any] | None, district_name: str) -> dict[str, Any]:
    """Select the district item matching the configured district name."""
    if not response:
        raise ValueError("高德 API 无响应")
    if response.get("status") != "1":
        info = response.get("info")
        infocode = response.get("infocode")
        raise ValueError(f"高德 API 返回失败：info={info} infocode={infocode}")

    districts = response.get("districts")
    if not isinstance(districts, list) or not districts:
        raise ValueError("高德 API 响应缺少 districts")

    for item in districts:
        if item.get("name") == district_name:
            return item
    raise ValueError(f"高德 API 响应未包含区县：{district_name}")


def build_target_districts(
    config: dict[str, Any] | None = None,
    client: AmapClient | None = None,
    processed_dir: str | Path | None = None,
    results_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Fetch configured target districts and write Step 4 outputs."""
    cfg = config or load_config()
    city_name = cfg["project"]["city"]
    district_names = cfg["target_districts"]["first_version"]
    amap_client = client or AmapClient()

    processed_path = Path(processed_dir) if processed_dir is not None else get_path("processed_dir", cfg)
    results_path = Path(results_dir) if results_dir is not None else get_path("results_dir", cfg)
    processed_path.mkdir(parents=True, exist_ok=True)
    results_path.mkdir(parents=True, exist_ok=True)

    districts_csv = processed_path / "target_districts.csv"
    boundaries_geojson = processed_path / "target_district_boundaries.geojson"
    warnings_md = results_path / "district_boundary_warnings.md"

    rows: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []
    warnings: list[str] = []

    for district_name in district_names:
        row = {
            "district_name": district_name,
            "city_name": city_name,
            "adcode": "",
            "center_lon": "",
            "center_lat": "",
            "has_boundary": False,
            "data_source": "amap_api",
        }
        try:
            response = amap_client.get_district(district_name, city=city_name)
            item = select_district_item(response, district_name)
            row["adcode"] = item.get("adcode", "")
            center = item.get("center", "")
            if center:
                center_lon, center_lat = parse_center(center)
                row["center_lon"] = center_lon
                row["center_lat"] = center_lat
            else:
                warnings.append(f"- {district_name}：缺少 center")

            try:
                geometry = parse_polyline(item.get("polyline", ""))
            except ValueError as exc:
                warnings.append(f"- {district_name}：{exc}")
            else:
                row["has_boundary"] = True
                features.append(
                    {
                        "type": "Feature",
                        "properties": {"district_name": district_name, "adcode": row["adcode"]},
                        "geometry": geometry,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"- {district_name}：{exc}")

        rows.append(row)

    with districts_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=DISTRICT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    geojson = {
        "type": "FeatureCollection",
        "name": "target_district_boundaries",
        "coord_system": "GCJ-02",
        "features": features,
    }
    boundaries_geojson.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")

    if warnings:
        warning_text = "\n".join(
            [
                "# 区县边界获取警告",
                "",
                "以下内容来自 Step 4 在线高德行政区划 API 获取与边界解析过程。",
                "",
                *warnings,
                "",
                "坐标系说明：高德返回坐标为 GCJ-02，本步不做坐标转换。",
            ]
        )
        warnings_md.write_text(warning_text, encoding="utf-8")
    elif warnings_md.exists():
        warnings_md.unlink()

    return {
        "districts_csv": districts_csv,
        "boundaries_geojson": boundaries_geojson,
        "warnings_md": warnings_md,
    }


def main() -> None:
    """Script entry point for Step 4."""
    outputs = build_target_districts()
    print(f"target districts: {outputs['districts_csv']}")
    print(f"target boundaries: {outputs['boundaries_geojson']}")
    if outputs["warnings_md"].exists():
        print(f"boundary warnings: {outputs['warnings_md']}")
    else:
        print("boundary warnings: none")


if __name__ == "__main__":
    main()
