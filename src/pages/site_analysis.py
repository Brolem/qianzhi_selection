"""Minimal Step 11 site-analysis page."""

from __future__ import annotations

from typing import Any

from src.pages.common import (
    available_districts,
    display_columns,
    get_streamlit,
    profile_top_rows,
    select_profile,
)


def render(st_module: Any | None = None) -> None:
    """Render the stable entry point for later Step 13 interactions."""
    st = get_streamlit(st_module)
    st.header("选址分析")
    st.caption("当前提供智能推荐结果预览；区域评估和单点评估尚未实施。")
    try:
        profile = select_profile(st, key="site_analysis_profile")
        districts = ["全部", *available_districts(profile)]
        district = st.selectbox(
            "目标区县",
            districts,
            key="site_analysis_district",
        )
        rows = profile_top_rows(
            profile,
            district_name=district,
            limit=5,
        )
        columns = [
            "grid_id",
            "district_name",
            profile.score_field,
            profile.rank_field,
            profile.level_field,
            profile.advantage_field,
            profile.risk_field,
        ]
        st.metric("当前有效网格", len(rows))
        st.dataframe(
            display_columns(rows, columns),
            use_container_width=True,
            hide_index=True,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
