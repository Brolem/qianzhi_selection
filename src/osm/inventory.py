"""OSM GPKG layer inventory for Step 3."""

from __future__ import annotations

import csv
import json
from itertools import islice
from pathlib import Path
from typing import Any

import fiona

try:
    from ..config import ensure_output_dirs, get_path
except ImportError:
    from src.config import ensure_output_dirs, get_path


POI_LAYERS = {
    "gis_osm_pois_free",
    "gis_osm_pois_a_free",
    "gis_osm_pofw_free",
    "gis_osm_pofw_a_free",
}
ROAD_TRANSPORT_LAYERS = {
    "gis_osm_roads_free",
    "gis_osm_railways_free",
    "gis_osm_traffic_free",
    "gis_osm_traffic_a_free",
    "gis_osm_transport_free",
    "gis_osm_transport_a_free",
}
LANDUSE_LAYERS = {"gis_osm_landuse_a_free"}
BOUNDARY_PLACE_LAYERS = {
    "gis_osm_adminareas_a_free",
    "gis_osm_places_free",
    "gis_osm_places_a_free",
}

INVENTORY_COLUMNS = [
    "layer_name",
    "geometry_type",
    "row_count",
    "crs",
    "columns",
    "sample_tags_or_fields",
    "recommended_group",
]


def classify_layer_group(layer_name: str) -> str:
    """Classify a real Geofabrik layer name into the Step 3 recommended group."""
    if layer_name in POI_LAYERS:
        return "POI"
    if layer_name in ROAD_TRANSPORT_LAYERS:
        return "road/transport"
    if layer_name in LANDUSE_LAYERS:
        return "landuse"
    if layer_name in BOUNDARY_PLACE_LAYERS:
        return "boundary/place"
    return "background"


def _serialize_properties(properties: Any) -> dict[str, Any]:
    """Convert Fiona properties into a JSON-serializable plain dict."""
    return dict(properties) if properties is not None else {}


def inspect_gpkg_layers(gpkg_path: str | Path) -> list[dict[str, Any]]:
    """Inspect every layer in a GPKG without aggregating spatial features."""
    path = Path(gpkg_path)
    if not path.exists():
        raise FileNotFoundError(f"OSM GPKG 文件不存在：{path}。请检查 data/raw/osm_guizhou/guizhou.gpkg")

    records: list[dict[str, Any]] = []
    for layer_name in fiona.listlayers(path):
        with fiona.open(path, layer=layer_name) as collection:
            property_columns = list(collection.schema.get("properties", {}).keys())
            columns = [*property_columns, "geometry"]
            samples = [_serialize_properties(feature.get("properties")) for feature in islice(collection, 3)]
            crs_text = collection.crs_wkt or str(collection.crs or "")
            records.append(
                {
                    "layer_name": layer_name,
                    "geometry_type": str(collection.schema.get("geometry", "")),
                    "row_count": len(collection),
                    "crs": crs_text,
                    "columns": ",".join(columns),
                    "sample_tags_or_fields": json.dumps(samples, ensure_ascii=False),
                    "recommended_group": classify_layer_group(layer_name),
                }
            )
    return records


def build_markdown_report(records: list[dict[str, Any]]) -> str:
    """Build a concise Markdown report for the OSM inventory."""
    lines = [
        "# OSM 贵州 GPKG 图层盘点",
        "",
        f"共识别 {len(records)} 个图层。本步骤只做图层盘点与空间数据可用性检查，不生成评分结果，不生成 1km 评价网格，不修改 Streamlit 页面。",
        "",
        "## 推荐使用图层",
        "",
    ]
    group_titles = [
        ("POI", "POI 图层"),
        ("road/transport", "road/transport 图层"),
        ("landuse", "landuse 图层"),
        ("boundary/place", "boundary/place 图层"),
    ]
    for group, title in group_titles:
        lines.extend([f"### {title}", ""])
        group_records = [record for record in records if record["recommended_group"] == group]
        if not group_records:
            lines.append("- 未识别到该类推荐使用图层。")
        for record in group_records:
            lines.append(
                f"- `{record['layer_name']}`：几何类型 `{record['geometry_type']}`，"
                f"{record['row_count']} 条，字段 `{record['columns']}`。"
            )
        lines.append("")

    admin_record = next((record for record in records if record["layer_name"] == "gis_osm_adminareas_a_free"), None)
    admin_count = admin_record["row_count"] if admin_record else "未识别"
    lines.extend(
        [
            "## 可用性判断",
            "",
            f"- `gis_osm_adminareas_a_free` 当前有 {admin_count} 条边界区域，可支撑区域级粗筛。",
            "- `gis_osm_roads_free` 可用于道路长度、道路密度和路口相关空间特征。",
            "- POI、交通/运输、土地利用图层可用于后续空间特征构建。",
            "- 其他图层当前只作为背景参考，不进入本步骤推荐使用清单。",
            "",
            "## 全部图层",
            "",
        ]
    )
    for record in records:
        lines.append(
            f"- `{record['layer_name']}`：{record['row_count']} 条，"
            f"几何类型 `{record['geometry_type']}`，分组 `{record['recommended_group']}`。"
        )
    return "\n".join(lines)


def write_inventory_outputs(records: list[dict[str, Any]], csv_path: str | Path, markdown_path: str | Path) -> None:
    """Write OSM inventory CSV and Markdown report."""
    csv_output = Path(csv_path)
    markdown_output = Path(markdown_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in INVENTORY_COLUMNS})
    markdown_output.write_text(build_markdown_report(records), encoding="utf-8")


def run_inventory() -> dict[str, Path]:
    """Run Step 3 OSM inventory against the local Guizhou GPKG."""
    ensure_output_dirs()
    gpkg_path = get_path("raw_osm_data") / "guizhou.gpkg"
    metadata_dir = get_path("results_metadata")
    records = inspect_gpkg_layers(gpkg_path)
    csv_path = metadata_dir / "osm_guizhou_layer_inventory.csv"
    markdown_path = metadata_dir / "osm_guizhou_layer_inventory.md"
    write_inventory_outputs(records, csv_path, markdown_path)
    return {"csv": csv_path, "markdown": markdown_path}


def main() -> None:
    """CLI entry point."""
    outputs = run_inventory()
    for path in outputs.values():
        print(path)


if __name__ == "__main__":
    main()
