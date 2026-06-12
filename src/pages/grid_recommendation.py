"""Minimal Step 11 grid-recommendation page."""

from __future__ import annotations

from typing import Any

from src.pages.common import (
    available_districts,
    display_columns,
    get_streamlit,
    profile_top_rows,
    select_profile,
)
from src.ui.workbench import render_page_header


def recommendation_columns(profile) -> list[str]:
    """Return the exact score, metric, explanation and level fields."""
    return [
        "grid_id",
        "district_name",
        profile.score_field,
        profile.rank_field,
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        profile.synergy_field,
        profile.competition_pressure_field,
        "business_atmosphere",
        profile.advantage_field,
        profile.risk_field,
        profile.level_field,
    ]


def render(st_module: Any | None = None) -> None:
    """Render active Top 10 grid recommendations for one scoring profile."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "网格推荐",
        "按评分方案和区县查看活跃网格 Top 10、六维指标及风险解释。",
    )
    try:
        with st.container(border=True):
            st.subheader("筛选条件")
            profile_column, district_column = st.columns(2, gap="medium")
            with profile_column:
                profile = select_profile(
                    st,
                    key="grid_recommendation_profile",
                )
            with district_column:
                district = st.selectbox(
                    "区县",
                    ["全部", *available_districts(profile)],
                    key="grid_recommendation_district",
                )
        rows = profile_top_rows(
            profile,
            district_name=district,
            limit=10,
        )
        st.subheader("Top 10 推荐结果")
        st.dataframe(
            display_columns(rows, recommendation_columns(profile)),
            use_container_width=True,
            hide_index=True,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
