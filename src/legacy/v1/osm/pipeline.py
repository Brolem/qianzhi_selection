"""Download and process Geofabrik Guizhou OSM layers into spatial features."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

try:
    from ..config import ensure_output_dirs, get_path
except ImportError:
    from src.legacy.v1.config import ensure_output_dirs, get_path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_OSM_DIR = get_path("raw_osm_data")
PROCESSED_DIR = get_path("processed_osm_region")
RESULTS_DIR = get_path("results_metadata")
REPORTS_DIR = get_path("reports")

GPKG_URL = "https://download.geofabrik.de/asia/china/guizhou-latest-free.gpkg.zip"
SHP_URL = "https://download.geofabrik.de/asia/china/guizhou-latest-free.shp.zip"

POI_OUTPUT_COLUMNS = [
    "region_id",
    "school_count",
    "hospital_count",
    "bus_stop_count",
    "restaurant_count",
    "convenience_count",
    "supermarket_count",
    "mall_count",
    "office_count",
]
ROAD_OUTPUT_COLUMNS = ["region_id", "road_length_total", "road_density", "intersection_count"]
LANDUSE_OUTPUT_COLUMNS = [
    "region_id",
    "residential_area",
    "commercial_area",
    "retail_area",
    "industrial_area",
    "farmland_area",
]
REQUIRED_COLUMNS = {"fclass"}
POI_CLASSES = {
    "school": "school_count",
    "hospital": "hospital_count",
    "bus_stop": "bus_stop_count",
    "restaurant": "restaurant_count",
    "fast_food": "restaurant_count",
    "cafe": "restaurant_count",
    "convenience": "convenience_count",
    "supermarket": "supermarket_count",
    "mall": "mall_count",
    "department_store": "mall_count",
    "office": "office_count",
}
LANDUSE_CLASSES = {
    "residential": "residential_area",
    "commercial": "commercial_area",
    "retail": "retail_area",
    "industrial": "industrial_area",
    "farmland": "farmland_area",
}
MAIN_ROADS = {"motorway", "trunk", "primary"}
SECONDARY_ROADS = {"secondary", "tertiary"}
LOCAL_ROADS = {"residential", "unclassified", "service", "living_street"}
WALK_ROADS = {"footway", "pedestrian", "path", "steps", "track"}


@dataclass(frozen=True)
class OsmSource:
    """Resolved OSM input source."""

    data_path: Path
    source_url: str
    source_kind: str
    zip_path: Path | None = None


def download_file(url: str, output_path: Path, timeout_seconds: int = 120) -> Path:
    """Download a URL to a local path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout_seconds) as response, output_path.open("wb") as file:
        shutil.copyfileobj(response, file)
    return output_path


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    """Extract a zip archive to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(output_dir)


def find_first_file(root: Path, suffix: str) -> Path | None:
    """Find the first file by suffix in deterministic order."""
    files = sorted(path for path in root.rglob(f"*{suffix}") if path.is_file())
    return files[0] if files else None


def list_layers(path: Path) -> list[str]:
    """List layers for GPKG or Shapefile inputs."""
    if path.suffix.lower() == ".gpkg":
        try:
            import fiona

            return list(fiona.listlayers(path))
        except ModuleNotFoundError:
            layers = gpd.list_layers(path)
            return layers["name"].astype(str).tolist()
    if path.suffix.lower() == ".shp":
        return [path.stem]
    if path.is_dir():
        return [shp.stem for shp in sorted(path.rglob("*.shp"))]
    return []


def read_layer(path: Path, layer_name: str | None = None) -> gpd.GeoDataFrame:
    """Read one OSM layer from GPKG or Shapefile."""
    if path.suffix.lower() == ".gpkg":
        return gpd.read_file(path, layer=layer_name)
    if path.suffix.lower() == ".shp":
        return gpd.read_file(path)
    matches = sorted(item for item in path.rglob(f"{layer_name}.shp") if item.is_file())
    if not matches:
        raise FileNotFoundError(f"未找到图层文件：{layer_name}")
    return gpd.read_file(matches[0])


def inspect_layers(path: Path) -> list[dict[str, Any]]:
    """Read layer names, columns, feature counts, geometry types, and CRS."""
    records: list[dict[str, Any]] = []
    for layer_name in list_layers(path):
        try:
            frame = read_layer(path, layer_name)
            records.append(
                {
                    "layer_name": layer_name,
                    "feature_count": len(frame),
                    "columns": ",".join(str(column) for column in frame.columns),
                    "geometry_types": ",".join(sorted(frame.geometry.geom_type.dropna().astype(str).unique())),
                    "crs": str(frame.crs) if frame.crs else "",
                }
            )
        except Exception as exc:
            records.append(
                {
                    "layer_name": layer_name,
                    "feature_count": "",
                    "columns": "",
                    "geometry_types": "",
                    "crs": "",
                    "error": str(exc),
                }
            )
    return records


def write_layer_inventory(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write layer inventory records to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["layer_name", "feature_count", "columns", "geometry_types", "crs", "error"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {field: record.get(field, "") for field in fieldnames}
            writer.writerow(row)


def pick_layer_name(inventory: list[dict[str, Any]], required_text: str) -> str | None:
    """Pick the first layer name containing exact lowercase text."""
    required_text = required_text.lower()
    for record in inventory:
        layer_name = str(record.get("layer_name", ""))
        if required_text in layer_name.lower():
            return layer_name
    return None


def pick_first_layer_name(inventory: list[dict[str, Any]], required_texts: list[str]) -> str | None:
    """Pick the first layer name matching any exact lowercase text in priority order."""
    for required_text in required_texts:
        layer_name = pick_layer_name(inventory, required_text)
        if layer_name:
            return layer_name
    return None


def require_columns(frame: gpd.GeoDataFrame, columns: set[str], layer_name: str) -> None:
    """Raise if a layer misses required columns."""
    missing = sorted(column for column in columns if column not in frame.columns)
    if missing:
        raise KeyError(f"`{layer_name}` 缺少必要字段：{', '.join(missing)}")


def classify_road_type(fclass: str) -> str:
    """Classify an exact OSM road fclass value."""
    value = str(fclass)
    if value in MAIN_ROADS:
        return "main"
    if value in SECONDARY_ROADS:
        return "secondary"
    if value in LOCAL_ROADS:
        return "local"
    if value in WALK_ROADS:
        return "walk"
    return ""


def projected(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project geographic data to a metric CRS for area and length calculations."""
    if frame.empty:
        return frame
    if frame.crs is None:
        raise ValueError("空间图层缺少 CRS，不能计算长度或面积。")
    return frame.to_crs(frame.estimate_utm_crs())


def choose_id_column(frame: gpd.GeoDataFrame) -> str | None:
    """Choose a stable existing identifier column from observed boundary fields."""
    for column in ["osm_id", "id"]:
        if column in frame.columns:
            return column
    return None


def choose_name_column(frame: gpd.GeoDataFrame) -> str | None:
    """Choose an existing name column from observed boundary fields."""
    for column in ["name", "name_en"]:
        if column in frame.columns:
            return column
    return None


def build_boundary_regions(boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame | None:
    """Build region polygons from an observed OSM boundary layer."""
    if boundaries.empty:
        return None
    id_column = choose_id_column(boundaries)
    name_column = choose_name_column(boundaries)
    if not id_column or not name_column:
        return None
    polygons = boundaries[boundaries.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if len(polygons) <= 1:
        return None
    regions = polygons[[id_column, name_column, "geometry"]].copy()
    regions = regions.rename(columns={id_column: "region_id", name_column: "region_name"})
    regions["region_id"] = regions["region_id"].astype(str)
    regions["region_name"] = regions["region_name"].astype(str)
    return regions[["region_id", "region_name", "geometry"]]


def build_grid_regions(source_frame: gpd.GeoDataFrame, grid_size_degrees: float = 0.25) -> gpd.GeoDataFrame:
    """Build internal evaluation grid regions over the source data extent."""
    if source_frame.empty:
        raise ValueError("无法基于空图层生成评价网格。")
    source_wgs = source_frame.to_crs("EPSG:4326") if source_frame.crs else source_frame.set_crs("EPSG:4326")
    minx, miny, maxx, maxy = source_wgs.total_bounds
    rows: list[dict[str, Any]] = []
    serial = 1
    x_steps = math.ceil((maxx - minx) / grid_size_degrees)
    y_steps = math.ceil((maxy - miny) / grid_size_degrees)
    for x_index in range(x_steps):
        for y_index in range(y_steps):
            x1 = minx + x_index * grid_size_degrees
            y1 = miny + y_index * grid_size_degrees
            cell = box(x1, y1, min(x1 + grid_size_degrees, maxx), min(y1 + grid_size_degrees, maxy))
            if source_wgs.intersects(cell).any():
                rows.append(
                    {
                        "region_id": f"grid_{serial:06d}",
                        "region_name": f"评价网格{serial:06d}",
                        "geometry": cell,
                    }
                )
                serial += 1
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def spatial_count_by_region(
    features: gpd.GeoDataFrame,
    regions: gpd.GeoDataFrame,
    feature_column: str,
    output_columns: list[str],
) -> pd.DataFrame:
    """Count classified features inside each region."""
    result = pd.DataFrame({"region_id": regions["region_id"].astype(str)})
    for column in output_columns:
        if column != "region_id":
            result[column] = 0
    if features.empty:
        return result
    aligned_features = features.to_crs(regions.crs)
    joined = gpd.sjoin(aligned_features, regions[["region_id", "geometry"]], how="inner", predicate="within")
    grouped = joined.groupby(["region_id", feature_column]).size()
    for (region_id, class_column), count in grouped.items():
        if class_column in result.columns:
            result.loc[result["region_id"].astype(str).eq(str(region_id)), class_column] = int(count)
    return result


def classify_poi_counts(pois: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build POI count features by region."""
    require_columns(pois, REQUIRED_COLUMNS, "POI 图层")
    selected = pois.copy()
    selected["poi_feature"] = selected["fclass"].map(POI_CLASSES).fillna("")
    selected = selected[selected["poi_feature"].ne("")]
    return spatial_count_by_region(selected, regions, "poi_feature", POI_OUTPUT_COLUMNS)


def build_road_features(roads: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build road length, density, and intersection count features by region."""
    require_columns(roads, REQUIRED_COLUMNS, "道路图层")
    selected = roads.copy()
    selected["road_type"] = selected["fclass"].map(classify_road_type)
    selected = selected[selected["road_type"].ne("")]
    metric_regions = projected(regions)
    metric_roads = selected.to_crs(metric_regions.crs)
    metric_regions = metric_regions.copy()
    metric_regions["region_area_sq_km"] = metric_regions.geometry.area / 1_000_000
    rows: list[dict[str, Any]] = []
    for _, region in metric_regions.iterrows():
        region_roads = metric_roads[metric_roads.intersects(region.geometry)].copy()
        road_length_total = float(region_roads.geometry.intersection(region.geometry).length.sum())
        road_density = road_length_total / float(region["region_area_sq_km"]) if region["region_area_sq_km"] else 0.0
        points: Counter[tuple[float, float]] = Counter()
        for geometry in region_roads.geometry:
            if geometry.is_empty:
                continue
            lines = list(geometry.geoms) if geometry.geom_type == "MultiLineString" else [geometry]
            for line in lines:
                if line.geom_type != "LineString":
                    continue
                for coordinate in line.coords:
                    points[(round(coordinate[0], 3), round(coordinate[1], 3))] += 1
        rows.append(
            {
                "region_id": str(region["region_id"]),
                "road_length_total": road_length_total,
                "road_density": road_density,
                "intersection_count": sum(1 for count in points.values() if count >= 3),
            }
        )
    return pd.DataFrame(rows, columns=ROAD_OUTPUT_COLUMNS)


def build_landuse_features(landuse: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build selected landuse area features by region."""
    require_columns(landuse, REQUIRED_COLUMNS, "土地利用图层")
    selected = landuse.copy()
    selected["landuse_feature"] = selected["fclass"].map(LANDUSE_CLASSES).fillna("")
    selected = selected[selected["landuse_feature"].ne("")]
    metric_regions = projected(regions)
    metric_landuse = selected.to_crs(metric_regions.crs)
    rows: list[dict[str, Any]] = []
    for _, region in metric_regions.iterrows():
        row = {column: 0.0 for column in LANDUSE_OUTPUT_COLUMNS}
        row["region_id"] = str(region["region_id"])
        region_landuse = metric_landuse[metric_landuse.intersects(region.geometry)].copy()
        for _, item in region_landuse.iterrows():
            column = item["landuse_feature"]
            row[column] += float(item.geometry.intersection(region.geometry).area)
        rows.append(row)
    return pd.DataFrame(rows, columns=LANDUSE_OUTPUT_COLUMNS)


def write_report(
    *,
    output_path: Path,
    status: str,
    source: OsmSource | None,
    inventory: list[dict[str, Any]],
    aggregation_unit: str,
    outputs: dict[str, Path],
    notes: list[str],
) -> None:
    """Write the OSM processing report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# OSM 贵州空间数据处理记录",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 状态：`{status}`",
        f"- 聚合单元：{aggregation_unit}",
    ]
    if source:
        lines.extend(
            [
                f"- 数据来源：{source.source_url}",
                f"- 数据类型：{source.source_kind}",
                f"- 数据路径：`{source.data_path}`",
            ]
        )
        if source.zip_path and source.zip_path.exists():
            lines.append(f"- 压缩包大小：{source.zip_path.stat().st_size} 字节")
    lines.extend(["", "## 1. 图层清单", ""])
    if inventory:
        lines.extend(f"- `{item.get('layer_name', '')}`：{item.get('feature_count', '')} 条" for item in inventory)
    else:
        lines.append("- 未读取到图层。")
    lines.extend(["", "## 2. 输出文件", ""])
    if outputs:
        lines.extend(f"- `{name}`：`{path}`" for name, path in outputs.items())
    else:
        lines.append("- 无输出文件。")
    lines.extend(["", "## 3. 说明与阻塞", ""])
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- 无阻塞。")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def prepare_osm_source(raw_dir: Path, prefer_download: bool = True) -> OsmSource:
    """Resolve existing OSM source or download Geofabrik GPKG/SHP data."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing_gpkg = find_first_file(raw_dir, ".gpkg")
    if existing_gpkg:
        gpkg_zip = raw_dir / "guizhou-latest-free.gpkg.zip"
        return OsmSource(existing_gpkg, GPKG_URL, "gpkg", gpkg_zip if gpkg_zip.exists() else None)
    existing_shp_dir = raw_dir if list(raw_dir.rglob("*.shp")) else None
    if existing_shp_dir:
        shp_zip = raw_dir / "guizhou-latest-free.shp.zip"
        return OsmSource(existing_shp_dir, SHP_URL, "shp", shp_zip if shp_zip.exists() else None)
    if not prefer_download:
        raise FileNotFoundError("未发现本地 OSM GPKG 或 SHP 文件。")

    gpkg_zip = raw_dir / "guizhou-latest-free.gpkg.zip"
    try:
        download_file(GPKG_URL, gpkg_zip)
        extract_zip(gpkg_zip, raw_dir)
        gpkg = find_first_file(raw_dir, ".gpkg")
        if not gpkg:
            raise FileNotFoundError("GPKG 压缩包解压后未发现 .gpkg 文件。")
        return OsmSource(gpkg, GPKG_URL, "gpkg", gpkg_zip)
    except Exception:
        shp_zip = raw_dir / "guizhou-latest-free.shp.zip"
        download_file(SHP_URL, shp_zip)
        extract_zip(shp_zip, raw_dir)
        if not list(raw_dir.rglob("*.shp")):
            raise FileNotFoundError("SHP 压缩包解压后未发现 .shp 文件。")
        return OsmSource(raw_dir, SHP_URL, "shp", shp_zip)


def run_osm_guizhou_pipeline(
    *,
    project_root: Path = PROJECT_ROOT,
    download: bool = True,
    grid_size_degrees: float = 0.25,
) -> dict[str, Any]:
    """Run the full Geofabrik Guizhou OSM processing pipeline."""
    project_root = Path(project_root)
    ensure_output_dirs()
    raw_dir = get_path("raw_osm_data")
    processed_dir = get_path("processed_osm_region")
    results_dir = get_path("results_metadata")
    reports_dir = get_path("reports")
    processed_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "osm_guizhou_processing_report.md"
    inventory_path = results_dir / "osm_guizhou_layer_inventory.csv"
    notes: list[str] = []
    outputs: dict[str, Path] = {"layer_inventory": inventory_path}
    source: OsmSource | None = None
    inventory: list[dict[str, Any]] = []
    aggregation_unit = "未确定"

    try:
        source = prepare_osm_source(raw_dir, prefer_download=download)
        inventory = inspect_layers(source.data_path)
        write_layer_inventory(inventory, inventory_path)

        boundary_layer = pick_first_layer_name(inventory, ["boundaries", "adminareas"])
        poi_layer = pick_layer_name(inventory, "pois")
        traffic_layer = pick_layer_name(inventory, "traffic")
        road_layer = pick_layer_name(inventory, "roads")
        landuse_layer = pick_layer_name(inventory, "landuse")
        places_layer = pick_layer_name(inventory, "places")

        if not poi_layer:
            raise KeyError("未发现 POI 图层。")
        if not road_layer:
            raise KeyError("未发现道路图层。")
        if not landuse_layer:
            notes.append("未发现土地利用图层，跳过 landuse_features.csv。")

        pois = read_layer(source.data_path, poi_layer)
        if traffic_layer:
            traffic = read_layer(source.data_path, traffic_layer)
            if "fclass" in traffic.columns:
                pois = pd.concat([pois, traffic], ignore_index=True)
            else:
                notes.append(f"`{traffic_layer}` 缺少 `fclass`，未用于 POI 聚合。")
        roads = read_layer(source.data_path, road_layer)

        regions = None
        if boundary_layer:
            boundaries = read_layer(source.data_path, boundary_layer)
            regions = build_boundary_regions(boundaries)
        if regions is not None:
            aggregation_unit = "OSM 边界图层"
        else:
            regions = build_grid_regions(pois if not pois.empty else roads, grid_size_degrees=grid_size_degrees)
            aggregation_unit = "评价网格"
            notes.append("边界图层不可用或不能形成多个区域，已使用评价网格。")

        poi_features = classify_poi_counts(pois, regions)
        poi_path = processed_dir / "poi_features.csv"
        poi_features.to_csv(poi_path, index=False, encoding="utf-8-sig")
        outputs["poi_features"] = poi_path

        road_features = build_road_features(roads, regions)
        road_path = processed_dir / "road_features.csv"
        road_features.to_csv(road_path, index=False, encoding="utf-8-sig")
        outputs["road_features"] = road_path

        if landuse_layer:
            landuse = read_layer(source.data_path, landuse_layer)
            landuse_features = build_landuse_features(landuse, regions)
            landuse_path = processed_dir / "landuse_features.csv"
            landuse_features.to_csv(landuse_path, index=False, encoding="utf-8-sig")
            outputs["landuse_features"] = landuse_path

        if places_layer:
            places = read_layer(source.data_path, places_layer)
            place_columns = [column for column in ["osm_id", "fclass", "name", "population"] if column in places.columns]
            if place_columns:
                places_path = processed_dir / "osm_places.csv"
                places[place_columns].copy().to_csv(places_path, index=False, encoding="utf-8-sig")
                outputs["osm_places"] = places_path
            else:
                notes.append(f"`{places_layer}` 没有可保留的地点字段。")

        if boundary_layer:
            boundaries = read_layer(source.data_path, boundary_layer)
            boundary_columns = [column for column in ["osm_id", "code", "fclass", "name"] if column in boundaries.columns]
            if boundary_columns:
                boundaries_path = processed_dir / "osm_boundaries.csv"
                boundaries[boundary_columns].copy().to_csv(boundaries_path, index=False, encoding="utf-8-sig")
                outputs["osm_boundaries"] = boundaries_path
            else:
                notes.append(f"`{boundary_layer}` 没有可保留的边界字段。")

        if len(regions) <= 1:
            notes.append("当前聚合结果只有一个评价区域，不能形成多区域排序。")

        write_report(
            output_path=report_path,
            status="osm_guizhou_processed",
            source=source,
            inventory=inventory,
            aggregation_unit=aggregation_unit,
            outputs=outputs,
            notes=notes,
        )
        return {"status": "osm_guizhou_processed", "outputs": outputs, "report": report_path}
    except Exception as exc:
        notes.append(str(exc))
        if inventory:
            write_layer_inventory(inventory, inventory_path)
        write_report(
            output_path=report_path,
            status="blocked_osm_guizhou_processing",
            source=source,
            inventory=inventory,
            aggregation_unit=aggregation_unit,
            outputs=outputs if inventory_path.exists() else {},
            notes=notes,
        )
        return {"status": "blocked_osm_guizhou_processing", "report": report_path, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="下载并处理 Geofabrik 贵州 OSM 空间数据。")
    parser.add_argument("--no-download", action="store_true", help="只处理本地已存在的 OSM 文件。")
    parser.add_argument("--grid-size-degrees", type=float, default=0.25, help="评价网格边长，单位为经纬度。")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    result = run_osm_guizhou_pipeline(download=not args.no_download, grid_size_degrees=args.grid_size_degrees)
    print(result["status"])
    print(result["report"])
    for path in result.get("outputs", {}).values():
        print(path)


if __name__ == "__main__":
    main()
