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
    st.header("网格推荐")
    try:
        profile = select_profile(st, key="grid_recommendation_profile")
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
        st.dataframe(
            display_columns(rows, recommendation_columns(profile)),
            use_container_width=True,
            hide_index=True,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
