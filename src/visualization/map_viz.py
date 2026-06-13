"""Build v2 grid recommendation maps from Step 8 score results."""

from __future__ import annotations

import copy
import html
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import folium
import pandas as pd


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config import get_amap_map_config, get_path
from src.profile_catalog import (
    CUSTOM_PROFILES_DIR,
    DEFAULT_METADATA_PATH,
    DEFAULT_RESULT_PATH,
    ResultProfileSpec,
    available_profile_specs as catalog_available_profile_specs,
    default_profile_specs as catalog_default_profile_specs,
    discover_custom_profile_specs as catalog_discover_custom_profile_specs,
)


RESULTS_DIR = get_path("results_dir")
PROCESSED_DIR = get_path("processed_dir")
FIGURES_DIR = get_path("figures_dir")
DEFAULT_GEOJSON_PATH = PROCESSED_DIR / "candidate_grids.geojson"
BASE_RESULT_FIELDS = [
    "grid_id",
    "district_name",
    "centroid_lon",
    "centroid_lat",
    "has_poi_activity",
    "traffic_accessibility",
    "consumption_potential",
    "employment_customer_proxy",
    "business_atmosphere",
]
UNSAMPLED_FILL = "#E4E8E6"
INACTIVE_FILL = "#AEB7B3"
SCORE_COLORS = [
    (20.0, "#B34A42"),
    (40.0, "#D98252"),
    (60.0, "#E8B96B"),
    (80.0, "#5FA27C"),
    (math.inf, "#176B4A"),
]
_USE_ENV_CREDENTIALS = object()


MapProfileSpec = ResultProfileSpec


@dataclass(frozen=True)
class AmapJsCredentials:
    """Browser-side credentials for Amap JavaScript API 2.0."""

    api_key: str
    security_code: str


def load_amap_js_credentials(
    api_key: str | None = None,
    security_code: str | None = None,
) -> AmapJsCredentials | None:
    """Read the Amap JS credential pair without exposing their values."""
    resolved_key = (
        api_key if api_key is not None else os.getenv("AMAP_JS_KEY", "")
    ).strip()
    resolved_code = (
        security_code
        if security_code is not None
        else os.getenv("AMAP_JS_SECURITY_CODE", "")
    ).strip()
    if not resolved_key and not resolved_code:
        return None
    missing = []
    if not resolved_key:
        missing.append("AMAP_JS_KEY")
    if not resolved_code:
        missing.append("AMAP_JS_SECURITY_CODE")
    if missing:
        raise ValueError("高德 JS API 环境变量缺失：" + "、".join(missing))
    return AmapJsCredentials(
        api_key=resolved_key,
        security_code=resolved_code,
    )


def default_profile_specs(
    result_path: str | Path = DEFAULT_RESULT_PATH,
    figures_dir: str | Path = FIGURES_DIR,
    metadata_path: str | Path | None = None,
) -> dict[str, MapProfileSpec]:
    """Return shared Step 8 default profile specifications."""
    result = Path(result_path)
    resolved_metadata = (
        Path(metadata_path)
        if metadata_path is not None
        else result.parent / "profile_metadata.json"
    )
    return catalog_default_profile_specs(
        result,
        resolved_metadata,
        figures_dir,
    )


def _require_columns(
    frame: pd.DataFrame,
    required: list[str],
    path: Path,
) -> None:
    missing = [field for field in required if field not in frame.columns]
    if missing:
        raise KeyError(f"{path} 缺少字段：{', '.join(missing)}")


def _profile_required_fields(spec: MapProfileSpec) -> list[str]:
    return [
        *BASE_RESULT_FIELDS,
        spec.synergy_field,
        spec.competition_score_field,
        spec.score_field,
        spec.rank_field,
        spec.district_rank_field,
        spec.advantage_field,
        spec.risk_field,
        spec.level_field,
    ]


def load_profile_result(spec: MapProfileSpec) -> pd.DataFrame:
    """Load and validate one map profile result."""
    if not spec.result_path.exists():
        raise FileNotFoundError(f"评分结果不存在：{spec.result_path}")
    frame = pd.read_csv(spec.result_path, dtype={"adcode": str})
    _require_columns(frame, _profile_required_fields(spec), spec.result_path)
    if frame["grid_id"].duplicated().any():
        duplicates = sorted(
            frame.loc[frame["grid_id"].duplicated(keep=False), "grid_id"]
            .astype(str)
            .unique()
            .tolist()
        )
        raise ValueError(f"{spec.result_path} 存在重复网格：{', '.join(duplicates)}")

    numeric_fields = [
        "centroid_lon",
        "centroid_lat",
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        spec.synergy_field,
        spec.competition_score_field,
        spec.score_field,
    ]
    for field in numeric_fields:
        values = pd.to_numeric(frame[field], errors="coerce")
        if values.isna().any():
            raise ValueError(f"{spec.result_path} 中 {field} 必须为数字且不能包含空值")
        if field not in {"centroid_lon", "centroid_lat"} and not values.between(0, 100).all():
            raise ValueError(f"{spec.result_path} 中 {field} 必须位于 0-100")
        frame[field] = values.astype(float)

    activity = frame["has_poi_activity"]
    if activity.dtype != bool:
        if not activity.isin([True, False]).all():
            raise ValueError(f"{spec.result_path} 中 has_poi_activity 必须为布尔值")
        frame["has_poi_activity"] = activity.astype(bool)
    return frame


def discover_custom_profile_specs(
    custom_profiles_dir: str | Path = CUSTOM_PROFILES_DIR,
) -> dict[str, MapProfileSpec]:
    """Discover shared Step 8 custom profile specifications."""
    specs = catalog_discover_custom_profile_specs(custom_profiles_dir)
    for spec in specs.values():
        load_profile_result(spec)
    return specs


def available_profile_specs(
    result_path: str | Path = DEFAULT_RESULT_PATH,
    figures_dir: str | Path = FIGURES_DIR,
    custom_profiles_dir: str | Path = CUSTOM_PROFILES_DIR,
    metadata_path: str | Path | None = None,
) -> dict[str, MapProfileSpec]:
    """Return shared user-facing default and custom profile options."""
    result = Path(result_path)
    resolved_metadata = (
        Path(metadata_path)
        if metadata_path is not None
        else result.parent / "profile_metadata.json"
    )
    specs = catalog_available_profile_specs(
        result,
        resolved_metadata,
        figures_dir,
        custom_profiles_dir,
    )
    for spec in specs.values():
        load_profile_result(spec)
    return specs


def _out_of_china(lon: float, lat: float) -> bool:
    return lon < 72.004 or lon > 137.8347 or lat < 0.8293 or lat > 55.8271


def _transform_lat(lon: float, lat: float) -> float:
    value = (
        -100.0
        + 2.0 * lon
        + 3.0 * lat
        + 0.2 * lat * lat
        + 0.1 * lon * lat
        + 0.2 * math.sqrt(abs(lon))
    )
    value += (
        20.0 * math.sin(6.0 * lon * math.pi)
        + 20.0 * math.sin(2.0 * lon * math.pi)
    ) * 2.0 / 3.0
    value += (
        20.0 * math.sin(lat * math.pi)
        + 40.0 * math.sin(lat / 3.0 * math.pi)
    ) * 2.0 / 3.0
    value += (
        160.0 * math.sin(lat / 12.0 * math.pi)
        + 320.0 * math.sin(lat * math.pi / 30.0)
    ) * 2.0 / 3.0
    return value


def _transform_lon(lon: float, lat: float) -> float:
    value = (
        300.0
        + lon
        + 2.0 * lat
        + 0.1 * lon * lon
        + 0.1 * lon * lat
        + 0.1 * math.sqrt(abs(lon))
    )
    value += (
        20.0 * math.sin(6.0 * lon * math.pi)
        + 20.0 * math.sin(2.0 * lon * math.pi)
    ) * 2.0 / 3.0
    value += (
        20.0 * math.sin(lon * math.pi)
        + 40.0 * math.sin(lon / 3.0 * math.pi)
    ) * 2.0 / 3.0
    value += (
        150.0 * math.sin(lon / 12.0 * math.pi)
        + 300.0 * math.sin(lon / 30.0 * math.pi)
    ) * 2.0 / 3.0
    return value


def _gcj_delta(lon: float, lat: float) -> tuple[float, float]:
    semi_major = 6378245.0
    eccentricity = 0.00669342162296594323
    delta_lat = _transform_lat(lon - 105.0, lat - 35.0)
    delta_lon = _transform_lon(lon - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - eccentricity * magic * magic
    sqrt_magic = math.sqrt(magic)
    delta_lat = (
        delta_lat * 180.0
        / ((semi_major * (1 - eccentricity)) / (magic * sqrt_magic) * math.pi)
    )
    delta_lon = (
        delta_lon * 180.0
        / (semi_major / sqrt_magic * math.cos(rad_lat) * math.pi)
    )
    return delta_lon, delta_lat


def wgs84_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 coordinates to GCJ-02 within China."""
    longitude = float(lon)
    latitude = float(lat)
    if _out_of_china(longitude, latitude):
        return longitude, latitude
    delta_lon, delta_lat = _gcj_delta(longitude, latitude)
    return longitude + delta_lon, latitude + delta_lat


def gcj02_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    """Convert GCJ-02 coordinates to WGS84 for open-tile rendering."""
    longitude = float(lon)
    latitude = float(lat)
    if _out_of_china(longitude, latitude):
        return longitude, latitude
    delta_lon, delta_lat = _gcj_delta(longitude, latitude)
    return longitude - delta_lon, latitude - delta_lat


def _convert_coordinates(value: Any) -> Any:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        lon, lat = gcj02_to_wgs84(float(value[0]), float(value[1]))
        return [lon, lat, *value[2:]]
    if isinstance(value, list):
        return [_convert_coordinates(item) for item in value]
    raise ValueError("GeoJSON coordinates 结构无效")


def convert_geojson_to_wgs84(geojson: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied GeoJSON object converted for Folium rendering."""
    result = copy.deepcopy(geojson)
    coord_system = result.get("coord_system")
    if coord_system == "WGS84":
        return result
    if coord_system != "GCJ-02":
        raise ValueError(f"GeoJSON coord_system 不受支持：{coord_system}")
    if result.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON 顶层 type 必须为 FeatureCollection")
    for feature in result.get("features", []):
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {
            "Polygon",
            "MultiPolygon",
        }:
            raise ValueError("评价网格 geometry 必须为 Polygon 或 MultiPolygon")
        geometry["coordinates"] = _convert_coordinates(geometry.get("coordinates"))
    result["coord_system"] = "WGS84"
    return result


def score_color(score: float) -> str:
    """Return the fixed five-band color for a score in the 0-100 range."""
    value = float(score)
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"评分必须位于 0-100：{value}")
    for upper_bound, color in SCORE_COLORS:
        if value < upper_bound:
            return color
    return SCORE_COLORS[-1][1]


def _format_number(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return "—" if pd.isna(numeric) else f"{float(numeric):.2f}"


def _format_rank(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return "—" if pd.isna(numeric) else str(int(numeric))


def _map_center(frame: pd.DataFrame) -> list[float]:
    points = [
        gcj02_to_wgs84(row.centroid_lon, row.centroid_lat)
        for row in frame.itertuples(index=False)
    ]
    return [
        sum(lat for _, lat in points) / len(points),
        sum(lon for lon, _ in points) / len(points),
    ]


def _map_center_gcj02(frame: pd.DataFrame) -> list[float]:
    return [
        float(frame["centroid_lon"].mean()),
        float(frame["centroid_lat"].mean()),
    ]


def _detail_values(
    row: pd.Series | None,
    spec: MapProfileSpec,
    status: str,
) -> dict[str, str]:
    if row is None:
        return {
            "map_status": status,
            "map_score": "—",
            "map_rank": "—",
            "map_advantage": "尚未采集POI",
            "map_level": "未进入评分",
            "metric_traffic": "—",
            "metric_consumption": "—",
            "metric_employment": "—",
            "metric_synergy": "—",
            "metric_competition": "—",
            "metric_atmosphere": "—",
            "map_risk": "尚无评分依据",
        }
    active = bool(row["has_poi_activity"])
    if not active:
        return {
            "map_status": status,
            "map_score": "0.00",
            "map_rank": "—",
            "map_advantage": str(row[spec.advantage_field]),
            "map_level": str(row[spec.level_field]),
            "metric_traffic": "—",
            "metric_consumption": "—",
            "metric_employment": "—",
            "metric_synergy": "—",
            "metric_competition": "—",
            "metric_atmosphere": "—",
            "map_risk": str(row[spec.risk_field]),
        }
    return {
        "map_status": status,
        "map_score": _format_number(row[spec.score_field]),
        "map_rank": _format_rank(row[spec.rank_field]),
        "map_advantage": str(row[spec.advantage_field]),
        "map_level": str(row[spec.level_field]),
        "metric_traffic": _format_number(row["traffic_accessibility"]),
        "metric_consumption": _format_number(row["consumption_potential"]),
        "metric_employment": _format_number(row["employment_customer_proxy"]),
        "metric_synergy": _format_number(row[spec.synergy_field]),
        "metric_competition": _format_number(row[spec.competition_score_field]),
        "metric_atmosphere": _format_number(row["business_atmosphere"]),
        "map_risk": str(row[spec.risk_field]),
    }


def _load_geojson(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path} 顶层 type 必须为 FeatureCollection")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError(f"{path} 缺少 features")
    grid_ids: list[str] = []
    for feature in features:
        properties = feature.get("properties", {})
        if "grid_id" not in properties:
            raise KeyError(f"{path} 的网格 Feature 缺少 grid_id")
        grid_ids.append(str(properties["grid_id"]))
    duplicates = sorted(
        grid_id
        for grid_id in set(grid_ids)
        if grid_ids.count(grid_id) > 1
    )
    if duplicates:
        raise ValueError(f"{path} 存在重复网格：{', '.join(duplicates)}")
    return data


def _enrich_geojson(
    geojson: dict[str, Any],
    frame: pd.DataFrame,
    spec: MapProfileSpec,
    top_n: int,
) -> tuple[dict[str, Any], dict[str, int]]:
    rows = {
        str(row["grid_id"]): row
        for _, row in frame.iterrows()
    }
    geojson_ids = {
        str(feature["properties"]["grid_id"])
        for feature in geojson["features"]
    }
    missing = sorted(set(rows) - geojson_ids)
    if missing:
        raise ValueError("评分网格缺少 GeoJSON 面：" + ", ".join(missing))

    result = convert_geojson_to_wgs84(geojson)
    counts = {"uncollected": 0, "inactive": 0, "active": 0, "top": 0}
    for feature in result["features"]:
        properties = feature["properties"]
        grid_id = str(properties["grid_id"])
        row = rows.get(grid_id)
        if row is None:
            status = "未采集"
            fill_color = UNSAMPLED_FILL
            border_color = "#C8D0CD"
            border_weight = 0.45
            fill_opacity = 0.38
            counts["uncollected"] += 1
        elif not bool(row["has_poi_activity"]):
            status = "无POI活动"
            fill_color = INACTIVE_FILL
            border_color = "#7D8984"
            border_weight = 0.8
            fill_opacity = 0.58
            counts["inactive"] += 1
        else:
            status = "已评分"
            fill_color = score_color(float(row[spec.score_field]))
            rank = pd.to_numeric(
                pd.Series([row[spec.rank_field]]),
                errors="coerce",
            ).iloc[0]
            is_top = not pd.isna(rank) and int(rank) <= top_n
            border_color = "#112F25" if is_top else "#FFFFFF"
            border_weight = 3.0 if is_top else 0.8
            fill_opacity = 0.78
            counts["active"] += 1
            if is_top:
                counts["top"] += 1
        details = _detail_values(row, spec, status)
        properties.update(details)
        properties["fill_color"] = fill_color
        properties["border_color"] = border_color
        properties["border_weight"] = border_weight
        properties["fill_opacity"] = fill_opacity
    return result, counts


def _top_marker_payload(
    frame: pd.DataFrame,
    spec: MapProfileSpec,
    top_n: int,
) -> list[dict[str, Any]]:
    ranks = pd.to_numeric(frame[spec.rank_field], errors="coerce")
    top = frame.loc[
        frame["has_poi_activity"].astype(bool)
        & ranks.notna()
        & ranks.le(top_n)
    ].copy()
    top["_map_rank"] = ranks.loc[top.index].astype(int)
    top = top.sort_values("_map_rank")
    return [
        {
            "grid_id": str(row["grid_id"]),
            "rank": int(row["_map_rank"]),
            "position": [
                float(row["centroid_lon"]),
                float(row["centroid_lat"]),
            ],
        }
        for _, row in top.iterrows()
    ]


def _enrich_geojson_gcj02(
    geojson: dict[str, Any],
    frame: pd.DataFrame,
    spec: MapProfileSpec,
    top_n: int,
) -> tuple[dict[str, Any], dict[str, int]]:
    if geojson.get("coord_system") != "GCJ-02":
        raise ValueError("高德地图 GeoJSON coord_system 必须为 GCJ-02")
    rows = {
        str(row["grid_id"]): row
        for _, row in frame.iterrows()
    }
    geojson_ids = {
        str(feature["properties"]["grid_id"])
        for feature in geojson["features"]
    }
    missing = sorted(set(rows) - geojson_ids)
    if missing:
        raise ValueError("评分网格缺少 GeoJSON 面：" + ", ".join(missing))

    result = copy.deepcopy(geojson)
    counts = {"uncollected": 0, "inactive": 0, "active": 0, "top": 0}
    for feature in result["features"]:
        properties = feature["properties"]
        grid_id = str(properties["grid_id"])
        row = rows.get(grid_id)
        if row is None:
            status = "未采集"
            fill_color = UNSAMPLED_FILL
            border_color = "#C8D0CD"
            border_weight = 1
            fill_opacity = 0.38
            counts["uncollected"] += 1
        elif not bool(row["has_poi_activity"]):
            status = "无POI活动"
            fill_color = INACTIVE_FILL
            border_color = "#7D8984"
            border_weight = 1
            fill_opacity = 0.58
            counts["inactive"] += 1
        else:
            status = "已评分"
            fill_color = score_color(float(row[spec.score_field]))
            rank = pd.to_numeric(
                pd.Series([row[spec.rank_field]]),
                errors="coerce",
            ).iloc[0]
            is_top = not pd.isna(rank) and int(rank) <= top_n
            border_color = "#112F25" if is_top else "#FFFFFF"
            border_weight = 3 if is_top else 1
            fill_opacity = 0.78
            counts["active"] += 1
            if is_top:
                counts["top"] += 1
        properties.update(_detail_values(row, spec, status))
        properties["fill_color"] = fill_color
        properties["border_color"] = border_color
        properties["border_weight"] = border_weight
        properties["fill_opacity"] = fill_opacity
    return result, counts


def prepare_amap_payload(
    spec: MapProfileSpec,
    *,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
    top_n: int = 10,
) -> dict[str, Any]:
    """Prepare one GCJ-02 payload shared by Amap HTML rendering."""
    if top_n < 1:
        raise ValueError("top_n 必须大于 0")
    frame = load_profile_result(spec)
    top_markers = _top_marker_payload(frame, spec, top_n)
    geojson_file = Path(geojson_path)
    if geojson_file.exists():
        geojson = _load_geojson(geojson_file)
        enriched, counts = _enrich_geojson_gcj02(
            geojson,
            frame,
            spec,
            top_n,
        )
        return {
            "coord_system": "GCJ-02",
            "mode": "polygons",
            "profile_name": spec.profile_name,
            "center": _map_center_gcj02(frame),
            "geojson": enriched,
            "points": [],
            "top_markers": top_markers,
            "status_counts": counts,
        }

    points = []
    for _, row in frame.iterrows():
        active = bool(row["has_poi_activity"])
        status = "已评分" if active else "无POI活动"
        details = _detail_values(row, spec, status)
        points.append(
            {
                "grid_id": str(row["grid_id"]),
                "district_name": str(row["district_name"]),
                "position": [
                    float(row["centroid_lon"]),
                    float(row["centroid_lat"]),
                ],
                "fill_color": (
                    score_color(float(row[spec.score_field]))
                    if active
                    else INACTIVE_FILL
                ),
                **details,
            }
        )
    return {
        "coord_system": "GCJ-02",
        "mode": "points",
        "profile_name": spec.profile_name,
        "center": _map_center_gcj02(frame),
        "geojson": None,
        "points": points,
        "top_markers": top_markers,
        "status_counts": {
            "active": int(frame["has_poi_activity"].sum()),
            "inactive": int((~frame["has_poi_activity"]).sum()),
            "top": len(top_markers),
        },
    }


def _safe_script_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")


def build_amap_map_html(
    spec: MapProfileSpec,
    *,
    credentials: AmapJsCredentials,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
    map_config: dict[str, Any] | None = None,
) -> str:
    """Build a self-contained Amap JS API 2.0 document using GCJ-02."""
    if not isinstance(credentials, AmapJsCredentials):
        raise TypeError("credentials 必须为 AmapJsCredentials")
    settings = map_config or get_amap_map_config()
    payload = prepare_amap_payload(
        spec,
        geojson_path=geojson_path,
        top_n=int(settings["top_n"]),
    )
    replacements = {
        "__API_KEY__": _safe_script_json(credentials.api_key),
        "__SECURITY_CODE__": _safe_script_json(credentials.security_code),
        "__API_VERSION__": _safe_script_json(str(settings["js_api_version"])),
        "__MAP_STYLE__": _safe_script_json(str(settings["map_style"])),
        "__DEFAULT_ZOOM__": str(int(settings["default_zoom"])),
        "__MAP_HEIGHT__": str(int(settings["height"])),
        "__MAP_PAYLOAD__": _safe_script_json(payload),
        "__PROFILE_NAME__": html.escape(spec.profile_name),
        "__UNSAMPLED_FILL__": UNSAMPLED_FILL,
        "__INACTIVE_FILL__": INACTIVE_FILL,
    }
    document = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>黔址优选地图</title>
  <style>
    html,body,#map{width:100%;height:100%;margin:0;background:#f3f5f8}
    body{height:__MAP_HEIGHT__px;font-family:"Microsoft YaHei",Arial,sans-serif}
    .map-legend{position:absolute;left:18px;bottom:20px;z-index:20;
      padding:10px 12px;background:#fff;border:1px solid #cbd3cf;
      box-shadow:0 2px 8px rgba(0,0,0,.16);font-size:12px;line-height:1.75}
    .map-legend span{display:inline-block;width:13px;height:10px;
      margin-right:6px;border:1px solid #aeb7b3}
    .legend-top-rank{display:inline-flex;width:17px;height:17px;margin-right:6px;
      align-items:center;justify-content:center;box-sizing:border-box;
      border:2px solid #112f25;border-radius:50%;background:#fff;color:#112f25;
      font-size:10px;font-weight:800;line-height:1;vertical-align:middle}
    .map-popup{min-width:230px;padding:10px 12px;background:#fff;
      border:1px solid #d7dedb;box-shadow:0 2px 10px rgba(0,0,0,.18);
      color:#172033;font-size:12px;line-height:1.65}
    .map-popup strong{font-size:13px}
    .top-rank-badge{width:25px;height:25px;border-radius:50%;background:#fff;
      border:3px solid #112f25;color:#112f25;font-weight:800;text-align:center;
      line-height:19px;box-shadow:0 2px 5px rgba(0,0,0,.4)}
    .map-error{display:none;position:absolute;inset:16px;z-index:30;
      align-items:center;justify-content:center;padding:20px;background:#fff;
      border:1px solid #d7dedb;color:#7a271a;text-align:center}
  </style>
  <script>
    window._AMapSecurityConfig={securityJsCode:__SECURITY_CODE__};
  </script>
  <script src="https://webapi.amap.com/loader.js"></script>
</head>
<body>
  <div id="map"></div>
  <div class="map-legend">
    <strong>__PROFILE_NAME__评分图例</strong>
    <div><span style="background:#B34A42"></span>0-20</div>
    <div><span style="background:#D98252"></span>20-40</div>
    <div><span style="background:#E8B96B"></span>40-60</div>
    <div><span style="background:__INACTIVE_FILL__"></span>无 POI 活动</div>
    <div><span style="background:__UNSAMPLED_FILL__"></span>未采集网格</div>
    <div><b class="legend-top-rank">1</b>全局 Top 10</div>
    <div>坐标：GCJ-02</div>
  </div>
  <div id="map-error" class="map-error">
    高德地图加载失败，请检查 Web端(JS API) Key、安全密钥、域名白名单或网络连接。
  </div>
  <script>
    const API_KEY=__API_KEY__;
    const PAYLOAD=__MAP_PAYLOAD__;
    const escapeHtml=(value)=>String(value??"—")
      .replaceAll("&","&amp;").replaceAll("<","&lt;")
      .replaceAll(">","&gt;").replaceAll('"',"&quot;")
      .replaceAll("'","&#39;");
    const summaryHtml=(p)=>`<div class="map-popup"><strong>${escapeHtml(p.grid_id)}</strong><br>
      区县：${escapeHtml(p.district_name)}<br>数据状态：${escapeHtml(p.map_status)}<br>
      评分：${escapeHtml(p.map_score)}<br>全局排名：${escapeHtml(p.map_rank)}<br>
      主要优势：${escapeHtml(p.map_advantage)}</div>`;
    const detailHtml=(p)=>`<div class="map-popup"><strong>${escapeHtml(p.grid_id)}</strong><br>
      推荐等级：${escapeHtml(p.map_level)}<br>交通可达性：${escapeHtml(p.metric_traffic)}<br>
      消费潜力：${escapeHtml(p.metric_consumption)}<br>
      就业客群代理：${escapeHtml(p.metric_employment)}<br>
      共生业态：${escapeHtml(p.metric_synergy)}<br>
      低竞争得分：${escapeHtml(p.metric_competition)}<br>
      商业氛围：${escapeHtml(p.metric_atmosphere)}<br>
      主要风险：${escapeHtml(p.map_risk)}</div>`;
    AMapLoader.load({key:API_KEY,version:__API_VERSION__,plugins:[]}).then((AMap)=>{
      const map=new AMap.Map("map",{zoom:__DEFAULT_ZOOM__,center:PAYLOAD.center,
        mapStyle:__MAP_STYLE__,viewMode:"2D"});
      const hoverInfo=new AMap.InfoWindow({isCustom:true,offset:new AMap.Pixel(0,-10)});
      const detailInfo=new AMap.InfoWindow({isCustom:true,offset:new AMap.Pixel(0,-10)});
      const bindOverlay=(overlay,properties)=>{
        overlay.on("mouseover",(event)=>{
          hoverInfo.setContent(summaryHtml(properties));
          hoverInfo.open(map,event.lnglat);
        });
        overlay.on("mouseout",()=>hoverInfo.close());
        overlay.on("click",(event)=>{
          hoverInfo.close();
          detailInfo.setContent(detailHtml(properties));
          detailInfo.open(map,event.lnglat);
        });
      };
      if(PAYLOAD.mode==="polygons"){
        PAYLOAD.geojson.features.forEach((feature)=>{
          const geometry=feature.geometry;
          const groups=geometry.type==="Polygon"
            ? [geometry.coordinates] : geometry.coordinates;
          groups.forEach((path)=>{
            const polygon=new AMap.Polygon({path,strokeColor:feature.properties.border_color,
              strokeWeight:feature.properties.border_weight,
              fillColor:feature.properties.fill_color,
              fillOpacity:feature.properties.fill_opacity,
              cursor:"pointer",zIndex:feature.properties.border_weight>1?15:10});
            map.add(polygon);
            bindOverlay(polygon,feature.properties);
          });
        });
      }else{
        PAYLOAD.points.forEach((point)=>{
          const marker=new AMap.CircleMarker({center:point.position,radius:7,
            strokeColor:"#FFFFFF",strokeWeight:1,fillColor:point.fill_color,
            fillOpacity:.82,zIndex:10});
          map.add(marker);
          bindOverlay(marker,point);
        });
      }
      PAYLOAD.top_markers.forEach((item)=>{
        map.add(new AMap.Marker({position:item.position,
          content:`<div class="top-rank-badge">${item.rank}</div>`,
          offset:new AMap.Pixel(-12,-12),zIndex:30}));
      });
    }).catch(()=>{
      document.getElementById("map-error").style.display="flex";
    });
  </script>
</body>
</html>"""
    for token, value in replacements.items():
        document = document.replace(token, value)
    return document


def _legend_html(profile_name: str, include_uncollected: bool) -> str:
    uncollected = (
        f'<div><span style="background:{UNSAMPLED_FILL}"></span>未采集网格</div>'
        if include_uncollected
        else ""
    )
    return f"""
<div class="map-legend" style="position:fixed;bottom:24px;left:18px;z-index:9999;
background:white;border:1px solid #b8c1bd;padding:10px 12px;font-size:12px;
line-height:1.75;box-shadow:0 2px 8px rgba(0,0,0,.18);">
  <strong>{html.escape(profile_name)}评分图例</strong>
  <div><span style="background:#B34A42"></span>0-20</div>
  <div><span style="background:#D98252"></span>20-40</div>
  <div><span style="background:#E8B96B"></span>40-60</div>
  <div><span style="background:{INACTIVE_FILL}"></span>无 POI 活动</div>
  {uncollected}
  <div><b class="legend-top-rank">1</b>全局 Top 10</div>
</div>
<style>
.map-legend span {{display:inline-block;width:13px;height:10px;margin-right:6px;
border:1px solid #aeb7b3;}}
.legend-top-rank {{display:inline-flex;width:17px;height:17px;margin-right:6px;
align-items:center;justify-content:center;box-sizing:border-box;
border:2px solid #112F25;border-radius:50%;background:#fff;color:#112F25;
font-size:10px;font-weight:800;line-height:1;vertical-align:middle;}}
.top-rank-badge {{width:25px;height:25px;border-radius:50%;background:#fff;
border:3px solid #112F25;color:#112F25;font-weight:800;text-align:center;
line-height:19px;box-shadow:0 2px 5px rgba(0,0,0,.4);pointer-events:none;}}
.top-rank-marker {{pointer-events:none !important;}}
</style>
"""


def _add_top_markers(
    result_map: folium.Map,
    frame: pd.DataFrame,
    spec: MapProfileSpec,
    top_n: int,
) -> int:
    ranks = pd.to_numeric(frame[spec.rank_field], errors="coerce")
    top = frame.loc[
        frame["has_poi_activity"].astype(bool)
        & ranks.notna()
        & ranks.le(top_n)
    ].copy()
    top["_map_rank"] = ranks.loc[top.index].astype(int)
    top = top.sort_values("_map_rank")
    for _, row in top.iterrows():
        lon, lat = gcj02_to_wgs84(
            row["centroid_lon"],
            row["centroid_lat"],
        )
        rank = int(row["_map_rank"])
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div class="top-rank-badge">{rank}</div>',
                icon_size=(25, 25),
                icon_anchor=(12, 12),
                class_name="top-rank-marker",
            ),
            tooltip=f"全局第 {rank}",
        ).add_to(result_map)
    return len(top)


def _add_geojson_layer(
    result_map: folium.Map,
    geojson: dict[str, Any],
) -> None:
    folium.GeoJson(
        data=geojson,
        name="1km 评价网格",
        style_function=lambda feature: {
            "fillColor": feature["properties"]["fill_color"],
            "color": feature["properties"]["border_color"],
            "weight": feature["properties"]["border_weight"],
            "fillOpacity": feature["properties"]["fill_opacity"],
        },
        highlight_function=lambda _feature: {
            "weight": 3,
            "color": "#111111",
            "fillOpacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "grid_id",
                "district_name",
                "map_status",
                "map_score",
                "map_rank",
                "map_advantage",
            ],
            aliases=[
                "网格编号",
                "区县",
                "数据状态",
                "评分",
                "全局排名",
                "主要优势",
            ],
            sticky=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=[
                "grid_id",
                "district_name",
                "map_status",
                "map_level",
                "metric_traffic",
                "metric_consumption",
                "metric_employment",
                "metric_synergy",
                "metric_competition",
                "metric_atmosphere",
                "map_risk",
            ],
            aliases=[
                "网格编号",
                "区县",
                "数据状态",
                "推荐等级",
                "交通可达性",
                "消费潜力",
                "就业客群代理",
                "共生业态",
                "低竞争得分",
                "商业氛围",
                "主要风险",
            ],
            localize=True,
        ),
    ).add_to(result_map)


def _point_tooltip(row: pd.Series, spec: MapProfileSpec) -> str:
    return (
        f"网格编号：{html.escape(str(row['grid_id']))}<br>"
        f"区县：{html.escape(str(row['district_name']))}<br>"
        f"评分：{_format_number(row[spec.score_field])}<br>"
        f"全局排名：{_format_rank(row[spec.rank_field])}<br>"
        f"主要优势：{html.escape(str(row[spec.advantage_field]))}"
    )


def _point_popup(row: pd.Series, spec: MapProfileSpec) -> str:
    details = _detail_values(
        row,
        spec,
        "已评分" if bool(row["has_poi_activity"]) else "无POI活动",
    )
    return "<br>".join(
        [
            f"<b>{html.escape(str(row['grid_id']))}</b>",
            f"推荐等级：{html.escape(details['map_level'])}",
            f"交通可达性：{details['metric_traffic']}",
            f"消费潜力：{details['metric_consumption']}",
            f"就业客群代理：{details['metric_employment']}",
            f"共生业态：{details['metric_synergy']}",
            f"低竞争得分：{details['metric_competition']}",
            f"商业氛围：{details['metric_atmosphere']}",
            f"主要风险：{html.escape(details['map_risk'])}",
        ]
    )


def _build_point_fallback(
    frame: pd.DataFrame,
    spec: MapProfileSpec,
    top_n: int,
) -> folium.Map:
    result_map = folium.Map(
        location=_map_center(frame),
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
    )
    for _, row in frame.iterrows():
        lon, lat = gcj02_to_wgs84(row["centroid_lon"], row["centroid_lat"])
        active = bool(row["has_poi_activity"])
        color = (
            score_color(float(row[spec.score_field]))
            if active
            else INACTIVE_FILL
        )
        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="#FFFFFF",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.82,
            tooltip=folium.Tooltip(_point_tooltip(row, spec), sticky=True),
            popup=folium.Popup(_point_popup(row, spec), max_width=320),
        ).add_to(result_map)
    top_count = _add_top_markers(result_map, frame, spec, top_n)
    result_map.get_root().html.add_child(
        folium.Element(
            '<div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);'
            'z-index:9999;background:#fff;border:1px solid #b8c1bd;padding:8px 12px;">'
            "空间网格文件不存在，当前仅展示评分网格中心点</div>"
        )
    )
    result_map.get_root().html.add_child(
        folium.Element(_legend_html(spec.profile_name, include_uncollected=False))
    )
    result_map._qianzhi_status_counts = {
        "active": int(frame["has_poi_activity"].sum()),
        "inactive": int((~frame["has_poi_activity"]).sum()),
        "top": top_count,
    }
    return result_map


def build_profile_map(
    spec: MapProfileSpec,
    *,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
    top_n: int = 10,
) -> folium.Map:
    """Build one default or custom profile map."""
    if top_n < 1:
        raise ValueError("top_n 必须大于 0")
    frame = load_profile_result(spec)
    geojson_file = Path(geojson_path)
    if not geojson_file.exists():
        return _build_point_fallback(frame, spec, top_n)

    geojson = _load_geojson(geojson_file)
    enriched, counts = _enrich_geojson(geojson, frame, spec, top_n)
    result_map = folium.Map(
        location=_map_center(frame),
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
    )
    _add_geojson_layer(result_map, enriched)
    top_count = _add_top_markers(result_map, frame, spec, top_n)
    counts["top"] = top_count
    result_map.get_root().html.add_child(
        folium.Element(_legend_html(spec.profile_name, include_uncollected=True))
    )
    folium.LayerControl(collapsed=False).add_to(result_map)
    result_map._qianzhi_status_counts = counts
    return result_map


def build_grid_map(
    business_type: str,
    *,
    grid_path: str | Path = DEFAULT_RESULT_PATH,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
) -> folium.Map:
    """Backward-compatible wrapper for the two default profile identifiers."""
    specs = default_profile_specs(grid_path)
    if business_type not in specs:
        supported = ", ".join(specs)
        raise ValueError(
            f"不支持的 business_type：{business_type}。支持值：{supported}"
        )
    return build_profile_map(specs[business_type], geojson_path=geojson_path)


def _write_temp_html(target: Path, content: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=target.parent,
        suffix=".tmp",
    ) as file:
        file.write(content)
        return Path(file.name)


def write_default_maps(
    *,
    result_path: str | Path = DEFAULT_RESULT_PATH,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
    output_dir: str | Path = FIGURES_DIR,
    credentials: AmapJsCredentials | None | object = _USE_ENV_CREDENTIALS,
    map_config: dict[str, Any] | None = None,
) -> list[Path]:
    """Generate and atomically replace both default profile HTML maps."""
    output = Path(output_dir)
    specs = default_profile_specs(result_path, output)
    resolved_credentials = (
        load_amap_js_credentials()
        if credentials is _USE_ENV_CREDENTIALS
        else credentials
    )
    if resolved_credentials is not None and not isinstance(
        resolved_credentials,
        AmapJsCredentials,
    ):
        raise TypeError("credentials 必须为 AmapJsCredentials 或 None")
    targets = [
        output / "convenience_grid_map.html",
        output / "light_food_grid_map.html",
    ]
    if resolved_credentials is None:
        html_contents = [
            build_profile_map(
                specs["convenience"],
                geojson_path=geojson_path,
            ).get_root().render(),
            build_profile_map(
                specs["light_food"],
                geojson_path=geojson_path,
            ).get_root().render(),
        ]
    else:
        settings = map_config or get_amap_map_config()
        html_contents = [
            build_amap_map_html(
                specs["convenience"],
                credentials=resolved_credentials,
                geojson_path=geojson_path,
                map_config=settings,
            ),
            build_amap_map_html(
                specs["light_food"],
                credentials=resolved_credentials,
                geojson_path=geojson_path,
                map_config=settings,
            ),
        ]
    temporary = [
        _write_temp_html(target, content)
        for target, content in zip(targets, html_contents)
    ]
    previous = [
        target.read_bytes() if target.exists() else None
        for target in targets
    ]
    try:
        for source, target in zip(temporary, targets):
            os.replace(source, target)
    except Exception:
        for target, content in zip(targets, previous):
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)
    return targets


def main() -> None:
    """Generate the two default Step 9 HTML maps."""
    for path in write_default_maps():
        print(path)


if __name__ == "__main__":
    main()
