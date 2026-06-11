"""Generate aligned one-kilometer evaluation grids for target districts."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box, mapping
from shapely.ops import unary_union


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_path, load_config


METRIC_CRS = "EPSG:32648"
OUTPUT_CRS = "EPSG:4326"
GRID_FIELDS = [
    "grid_id",
    "district_name",
    "adcode",
    "centroid_lon",
    "centroid_lat",
    "area_km2",
    "geometry_wkt",
    "data_source",
]


def build_aligned_cells(
    bounds: tuple[float, float, float, float],
    grid_size_m: int,
) -> list[tuple[int, int, Polygon]]:
    """Build square cells aligned to integer multiples of the grid size."""
    if grid_size_m <= 0:
        raise ValueError("grid_size_m 必须大于 0")

    minx, miny, maxx, maxy = bounds
    start_x = math.floor(minx / grid_size_m) * grid_size_m
    start_y = math.floor(miny / grid_size_m) * grid_size_m
    end_x = math.ceil(maxx / grid_size_m) * grid_size_m
    end_y = math.ceil(maxy / grid_size_m) * grid_size_m

    cells: list[tuple[int, int, Polygon]] = []
    for x in range(int(start_x), int(end_x), grid_size_m):
        for y in range(int(start_y), int(end_y), grid_size_m):
            cells.append((x, y, box(x, y, x + grid_size_m, y + grid_size_m)))
    return cells


def polygonal_geometry(geometry: Any) -> Polygon | MultiPolygon | None:
    """Return only polygonal parts from an intersection result."""
    if geometry.is_empty:
        return None
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        polygons = [
            item
            for item in geometry.geoms
            if isinstance(item, (Polygon, MultiPolygon)) and not item.is_empty
        ]
        if polygons:
            merged = unary_union(polygons)
            if isinstance(merged, (Polygon, MultiPolygon)):
                return merged
    return None


def _district_boundary(
    metric_boundaries: gpd.GeoDataFrame,
    district_name: str,
    adcode: str,
) -> Polygon | MultiPolygon | None:
    matches = metric_boundaries[
        metric_boundaries["adcode"].astype(str).eq(adcode)
        & metric_boundaries["district_name"].astype(str).eq(district_name)
    ]
    if matches.empty:
        return None
    merged = unary_union(matches.geometry.tolist())
    return polygonal_geometry(merged)


def _fallback_geometry(
    center_lon: Any,
    center_lat: Any,
    grid_size_m: int,
    output_crs: str,
    metric_crs: str,
) -> Polygon:
    try:
        lon = float(center_lon)
        lat = float(center_lat)
    except (TypeError, ValueError) as exc:
        raise ValueError("缺少真实边界且中心点无效，无法生成评价网格") from exc

    center = gpd.GeoSeries.from_xy([lon], [lat], crs=output_crs).to_crs(metric_crs).iloc[0]
    half_size = grid_size_m / 2
    return box(
        center.x - half_size,
        center.y - half_size,
        center.x + half_size,
        center.y + half_size,
    )


def generate_evaluation_grids(
    boundaries: gpd.GeoDataFrame,
    district_info: pd.DataFrame,
    grid_size_m: int = 1000,
    metric_crs: str = METRIC_CRS,
    output_crs: str = OUTPUT_CRS,
) -> gpd.GeoDataFrame:
    """Generate clipped evaluation grids with deterministic district IDs."""
    if district_info.empty:
        raise ValueError("目标区县基础信息为空，无法生成评价网格")
    if grid_size_m <= 0:
        raise ValueError("grid_size_m 必须大于 0")

    source_boundaries = boundaries.copy()
    if source_boundaries.crs is None:
        source_boundaries = source_boundaries.set_crs(output_crs)
    if not source_boundaries.empty:
        source_boundaries["district_name"] = source_boundaries["district_name"].astype(str)
        source_boundaries["adcode"] = source_boundaries["adcode"].astype(str)
        metric_boundaries = source_boundaries.to_crs(metric_crs)
        cells = build_aligned_cells(tuple(metric_boundaries.total_bounds), grid_size_m)
    else:
        metric_boundaries = gpd.GeoDataFrame(
            {"district_name": [], "adcode": []},
            geometry=[],
            crs=metric_crs,
        )
        cells = []

    rows: list[dict[str, Any]] = []
    for district in district_info.to_dict("records"):
        district_name = str(district["district_name"])
        adcode = str(district["adcode"])
        boundary = _district_boundary(metric_boundaries, district_name, adcode)
        serial = 1

        if boundary is not None:
            for _, _, cell in cells:
                clipped = polygonal_geometry(cell.intersection(boundary))
                if clipped is None or clipped.area <= 0:
                    continue
                rows.append(
                    {
                        "grid_id": f"grid_{adcode}_{serial:06d}",
                        "district_name": district_name,
                        "adcode": adcode,
                        "area_km2": clipped.area / 1_000_000,
                        "data_source": "amap_boundary",
                        "geometry": clipped,
                    }
                )
                serial += 1
        else:
            fallback = _fallback_geometry(
                district.get("center_lon"),
                district.get("center_lat"),
                grid_size_m,
                output_crs,
                metric_crs,
            )
            rows.append(
                {
                    "grid_id": f"grid_{adcode}_000001",
                    "district_name": district_name,
                    "adcode": adcode,
                    "area_km2": fallback.area / 1_000_000,
                    "data_source": "demo_center",
                    "geometry": fallback,
                }
            )

    if not rows:
        raise ValueError("未生成任何评价网格")

    metric_grids = gpd.GeoDataFrame(rows, geometry="geometry", crs=metric_crs)
    metric_centers = metric_grids.geometry.centroid
    output_centers = gpd.GeoSeries(metric_centers, crs=metric_crs).to_crs(output_crs)
    output_grids = metric_grids.to_crs(output_crs)
    output_grids["centroid_lon"] = output_centers.x.to_numpy()
    output_grids["centroid_lat"] = output_centers.y.to_numpy()
    output_grids["area_km2"] = output_grids["area_km2"].astype(float)
    return output_grids[
        [
            "grid_id",
            "district_name",
            "adcode",
            "centroid_lon",
            "centroid_lat",
            "area_km2",
            "data_source",
            "geometry",
        ]
    ]


def write_grid_outputs(grids: gpd.GeoDataFrame, processed_dir: str | Path) -> dict[str, Path]:
    """Write Step 5 grid CSV and GeoJSON outputs."""
    output_dir = Path(processed_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "candidate_grids.csv"
    geojson_path = output_dir / "candidate_grids.geojson"

    csv_rows = []
    features = []
    for row in grids.itertuples(index=False):
        common = {
            "grid_id": str(row.grid_id),
            "district_name": str(row.district_name),
            "adcode": str(row.adcode),
            "centroid_lon": float(row.centroid_lon),
            "centroid_lat": float(row.centroid_lat),
            "area_km2": float(row.area_km2),
            "data_source": str(row.data_source),
        }
        csv_rows.append({**common, "geometry_wkt": row.geometry.wkt})
        features.append(
            {
                "type": "Feature",
                "properties": common,
                "geometry": mapping(row.geometry),
            }
        )

    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=GRID_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)

    geojson = {
        "type": "FeatureCollection",
        "name": "candidate_grids",
        "coord_system": "GCJ-02",
        "features": features,
    }
    geojson_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": csv_path, "geojson": geojson_path}


def build_evaluation_grid_outputs(
    config: dict[str, Any] | None = None,
    processed_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Load Step 4 outputs, generate grids, and write Step 5 outputs."""
    cfg = config or load_config()
    output_dir = Path(processed_dir) if processed_dir is not None else get_path("processed_dir", cfg)
    boundaries_path = output_dir / "target_district_boundaries.geojson"
    districts_path = output_dir / "target_districts.csv"
    if not boundaries_path.exists():
        raise FileNotFoundError(f"区县边界文件不存在：{boundaries_path}")
    if not districts_path.exists():
        raise FileNotFoundError(f"区县基础信息文件不存在：{districts_path}")

    boundaries = gpd.read_file(boundaries_path)
    district_info = pd.read_csv(districts_path, dtype={"adcode": str})
    grids = generate_evaluation_grids(
        boundaries,
        district_info,
        grid_size_m=int(cfg["project"]["grid_size_m"]),
    )
    return write_grid_outputs(grids, output_dir)


def main() -> None:
    """Script entry point for Step 5."""
    outputs = build_evaluation_grid_outputs()
    grid_rows = pd.read_csv(outputs["csv"], dtype={"adcode": str})
    print(f"evaluation grid csv: {outputs['csv']}")
    print(f"evaluation grid geojson: {outputs['geojson']}")
    print(f"grid count: {len(grid_rows)}")
    for district_name, count in grid_rows.groupby("district_name").size().items():
        print(f"{district_name}: {count}")


if __name__ == "__main__":
    main()
