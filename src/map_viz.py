"""Map visualization for two-stage site selection results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import folium
import pandas as pd

try:
    from .config import get_path
except ImportError:
    from config import get_path


GRID_STAGE_RESULT = get_path("results_grid_stage") / "grid_stage_score_result.csv"
REGION_STAGE_RESULT = get_path("results_region_stage") / "region_stage_score_result.csv"
FIGURES_DIR = get_path("figures")

BUSINESS_SCORE_COLUMNS = {
    "convenience": "convenience_score",
    "light_food": "light_food_score",
}
GRID_REQUIRED_COLUMNS = {
    "grid_id",
    "grid_region_name",
    "centroid_lon",
    "centroid_lat",
    "convenience_score",
    "light_food_score",
    "main_advantage",
    "main_risk",
}
REGION_REQUIRED_COLUMNS = {
    "region_id",
    "region_name",
    "convenience_score",
    "light_food_score",
    "main_advantage",
    "main_risk",
}


def _score_column_for(business_type: str) -> str:
    """Return the exact score column for a supported business type."""
    if business_type not in BUSINESS_SCORE_COLUMNS:
        supported = ", ".join(sorted(BUSINESS_SCORE_COLUMNS))
        raise ValueError(f"不支持的 business_type：{business_type}。支持值：{supported}")
    return BUSINESS_SCORE_COLUMNS[business_type]


def _require_columns(frame: pd.DataFrame, required_columns: set[str], path: Path) -> None:
    """Raise when a CSV does not contain the exact required columns."""
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise KeyError(f"{path} 缺少字段：{', '.join(missing)}")


def load_grid_result(path: str | Path = GRID_STAGE_RESULT) -> pd.DataFrame:
    """Load grid-stage result CSV using the configured output path."""
    result_path = Path(path)
    if not result_path.exists():
        raise FileNotFoundError(f"网格细筛结果不存在：{result_path}")
    frame = pd.read_csv(result_path)
    _require_columns(frame, GRID_REQUIRED_COLUMNS, result_path)
    return frame


def load_region_result(path: str | Path = REGION_STAGE_RESULT) -> pd.DataFrame:
    """Load region-stage result CSV using the configured output path."""
    result_path = Path(path)
    if not result_path.exists():
        raise FileNotFoundError(f"区域粗筛结果不存在：{result_path}")
    frame = pd.read_csv(result_path)
    _require_columns(frame, REGION_REQUIRED_COLUMNS, result_path)
    return frame


def _format_score(value: Any) -> str:
    """Format a numeric score for tooltip display."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return str(value)
    return f"{float(numeric):.3f}"


def _score_color(score: float, min_score: float, max_score: float) -> str:
    """Return a simple stepped color for a normalized score."""
    if max_score == min_score:
        ratio = 0.5
    else:
        ratio = (score - min_score) / (max_score - min_score)
    if ratio >= 0.75:
        return "#0f7b4f"
    if ratio >= 0.50:
        return "#3f9b71"
    if ratio >= 0.25:
        return "#d6a23f"
    return "#b64d3d"


def _grid_map_center(frame: pd.DataFrame) -> list[float]:
    """Calculate a map center from exact grid centroid fields."""
    lat = pd.to_numeric(frame["centroid_lat"], errors="coerce").dropna()
    lon = pd.to_numeric(frame["centroid_lon"], errors="coerce").dropna()
    if lat.empty or lon.empty:
        return [26.6, 106.7]
    return [float(lat.mean()), float(lon.mean())]


def build_grid_map(
    business_type: str,
    *,
    grid_path: str | Path = GRID_STAGE_RESULT,
) -> folium.Map:
    """Build a point map from grid-stage centroid fields."""
    score_column = _score_column_for(business_type)
    frame = load_grid_result(grid_path).copy()
    frame[score_column] = pd.to_numeric(frame[score_column], errors="coerce").fillna(0.0)

    result_map = folium.Map(location=_grid_map_center(frame), zoom_start=10, tiles="CartoDB positron")
    if frame.empty:
        result_map.get_root().html.add_child(folium.Element("<h3>暂无 1km 评价网格结果</h3>"))
        return result_map

    min_score = float(frame[score_column].min())
    max_score = float(frame[score_column].max())
    for _, row in frame.sort_values(score_column, ascending=False).iterrows():
        lat = pd.to_numeric(pd.Series([row["centroid_lat"]]), errors="coerce").iloc[0]
        lon = pd.to_numeric(pd.Series([row["centroid_lon"]]), errors="coerce").iloc[0]
        if pd.isna(lat) or pd.isna(lon):
            continue

        score = float(row[score_column])
        grid_id = str(row["grid_id"])
        region_name = str(row["grid_region_name"])
        advantage = str(row["main_advantage"])
        risk = str(row["main_risk"])
        tooltip = (
            f"网格编号：{grid_id}<br>"
            f"所属区域：{region_name}<br>"
            f"评分：{_format_score(score)}<br>"
            f"主要优势：{advantage}<br>"
            f"主要风险：{risk}"
        )
        folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=7,
            color=_score_color(score, min_score, max_score),
            fill=True,
            fill_opacity=0.75,
            tooltip=folium.Tooltip(tooltip, sticky=True),
        ).add_to(result_map)

    return result_map


def _region_list_html(frame: pd.DataFrame, score_column: str) -> str:
    """Render region-stage records as a readable HTML panel."""
    rows = []
    for _, row in frame.sort_values(score_column, ascending=False).iterrows():
        rows.append(
            "<tr>"
            f"<td>{row['region_id']}</td>"
            f"<td>{row['region_name']}</td>"
            f"<td>{_format_score(row[score_column])}</td>"
            f"<td>{row['main_advantage']}</td>"
            f"<td>{row['main_risk']}</td>"
            "</tr>"
        )
    table_rows = "\n".join(rows)
    return f"""
<div style="position:absolute; top:12px; left:12px; z-index:9999; max-height:420px;
            overflow:auto; background:white; padding:12px; border:1px solid #bbb;
            font-family:Arial, sans-serif; font-size:13px;">
  <strong>区域粗筛评分列表</strong>
  <table style="border-collapse:collapse; margin-top:8px;">
    <thead>
      <tr>
        <th style="border-bottom:1px solid #ccc; padding:4px;">region_id</th>
        <th style="border-bottom:1px solid #ccc; padding:4px;">region_name</th>
        <th style="border-bottom:1px solid #ccc; padding:4px;">score</th>
        <th style="border-bottom:1px solid #ccc; padding:4px;">main_advantage</th>
        <th style="border-bottom:1px solid #ccc; padding:4px;">main_risk</th>
      </tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</div>
"""


def build_region_map(
    business_type: str,
    *,
    region_path: str | Path = REGION_STAGE_RESULT,
) -> folium.Map:
    """Build a non-boundary region score panel without inventing region geometry."""
    score_column = _score_column_for(business_type)
    frame = load_region_result(region_path).copy()
    frame[score_column] = pd.to_numeric(frame[score_column], errors="coerce").fillna(0.0)

    result_map = folium.Map(location=[26.6, 106.7], zoom_start=7, tiles="CartoDB positron")
    result_map.get_root().html.add_child(folium.Element(_region_list_html(frame, score_column)))
    return result_map


def write_default_maps(
    *,
    grid_path: str | Path = GRID_STAGE_RESULT,
    region_path: str | Path = REGION_STAGE_RESULT,
    output_dir: str | Path = FIGURES_DIR,
) -> list[Path]:
    """Write default grid maps for the two supported business types."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    outputs = [
        output_path / "convenience_grid_map.html",
        output_path / "light_food_grid_map.html",
    ]
    build_grid_map("convenience", grid_path=grid_path).save(outputs[0])
    build_grid_map("light_food", grid_path=grid_path).save(outputs[1])
    # Validate region-stage inputs as part of Step 6 without fabricating region geometry.
    build_region_map("convenience", region_path=region_path)
    build_region_map("light_food", region_path=region_path)
    return outputs


def main() -> None:
    """CLI entry point for Step 6 map visualization."""
    for path in write_default_maps():
        print(path)


if __name__ == "__main__":
    main()
