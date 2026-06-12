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
from src.ui.workbench import render_page_header, render_workflow_steps


def render(st_module: Any | None = None) -> None:
    """Render the stable entry point for later Step 13 interactions."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "选址分析",
        "按评分方案和目标区县预览智能推荐结果；区域评估和单点评估尚未实施。",
    )
    render_workflow_steps(st, active_step=3)
    try:
        parameter_panel, result_panel = st.columns(
            [1, 2.4],
            gap="large",
        )
        with parameter_panel:
            with st.container(border=True):
                st.subheader("分析参数")
                profile = select_profile(st, key="site_analysis_profile")
                districts = ["全部", *available_districts(profile)]
                district = st.selectbox(
                    "目标区县",
                    districts,
                    key="site_analysis_district",
                )
                st.caption("当前步骤只读取已有评分结果，不重新计算评分。")
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
        with result_panel:
            with st.container(border=True):
                st.subheader("Top 5 推荐预览")
                st.metric("当前有效网格", len(rows))
                st.dataframe(
                    display_columns(rows, columns),
                    use_container_width=True,
                    hide_index=True,
                )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
