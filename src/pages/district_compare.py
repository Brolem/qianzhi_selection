"""Minimal Step 11 district-comparison page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.pages.common import (
    DISTRICT_SUMMARY_PATH,
    get_streamlit,
    load_required_csv,
)
from src.ui.workbench import render_page_header


DISTRICT_SUMMARY_FIELDS = [
    "district_name",
    "grid_count",
    "active_grid_count",
    "poi_total_count",
    "avg_convenience_score",
    "top_convenience_grid_id",
    "avg_light_food_score",
    "top_light_food_grid_id",
]


def load_district_comparison(
    path: str | Path = DISTRICT_SUMMARY_PATH,
):
    """Load the Step 8 district grouping summary."""
    return load_required_csv(path, DISTRICT_SUMMARY_FIELDS)[
        DISTRICT_SUMMARY_FIELDS
    ].copy()


def render(st_module: Any | None = None) -> None:
    """Render district grouping context without replacing grid ranking."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "区域对比",
        "对比三区网格规模、活跃样本、POI 总量和两类默认方案表现。",
    )
    try:
        frame = load_district_comparison()
    except (FileNotFoundError, KeyError) as exc:
        st.error(str(exc))
        return
    with st.container(border=True):
        st.subheader("三区汇总")
        st.dataframe(frame, use_container_width=True, hide_index=True)
    st.info(
        "区县对比仅用于背景画像和结果分组，最终推荐仍以 1km 评价网格评分为准。"
    )
