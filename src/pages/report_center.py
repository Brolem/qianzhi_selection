"""Step 10 report center in the Step 11 workbench."""

from __future__ import annotations

from typing import Any

from src.pages.common import get_streamlit
from src.reporting.report_generator import (
    active_profile_results,
    generate_site_report,
)
from src.visualization.map_viz import MapProfileSpec, available_profile_specs


def render_report_page(
    st: Any,
    business_type: str | None = None,
    *,
    profile_specs: dict[str, MapProfileSpec] | None = None,
    report_generator_func: Any = generate_site_report,
) -> None:
    """Render button-triggered default or custom DeepSeek reports."""
    del business_type
    st.header("智能报告")
    try:
        specs = profile_specs or available_profile_specs()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    if not specs:
        st.warning("没有可用的评分方案。")
        return

    selected_label = st.selectbox(
        "评分方案",
        list(specs),
    )
    profile = specs[selected_label]
    try:
        active = active_profile_results(profile)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    if active.empty:
        st.warning("该评分方案没有可用于生成报告的活跃排名网格。")
        return

    option_to_grid: dict[str, str] = {}
    for _, row in active.iterrows():
        rank = int(float(row[profile.rank_field]))
        score = float(row[profile.score_field])
        grid_id = str(row["grid_id"])
        label = f"#{rank}｜{row['district_name']}｜{grid_id}｜{score:.2f}分"
        option_to_grid[label] = grid_id
    selected_grid_label = st.selectbox(
        "评价网格",
        list(option_to_grid),
    )
    selected_grid_id = option_to_grid[selected_grid_label]
    state_prefix = f"site_report:{profile.profile_id}:{selected_grid_id}"
    result_key = f"{state_prefix}:result"
    error_key = f"{state_prefix}:error"

    if st.button("生成智能报告"):
        try:
            st.session_state[result_key] = report_generator_func(
                selected_grid_id,
                profile,
                use_llm=True,
            )
            st.session_state.pop(error_key, None)
        except Exception as exc:
            st.session_state.pop(result_key, None)
            st.session_state[error_key] = str(exc)

    if error_key in st.session_state:
        st.error(st.session_state[error_key])
        if st.button("使用模板报告"):
            try:
                st.session_state[result_key] = report_generator_func(
                    selected_grid_id,
                    profile,
                    use_llm=False,
                )
                st.session_state.pop(error_key, None)
            except Exception as exc:
                st.error(str(exc))

    report = st.session_state.get(result_key)
    if report is None:
        return
    if report.mode == "template":
        st.info("当前展示规则模板报告。")
    elif report.used_fallback:
        st.info(f"DeepSeek 模型：{report.model}（Pro 暂不可用，已回退）。")
    else:
        st.info(f"DeepSeek 模型：{report.model}。")
    st.markdown(report.content)
    st.download_button(
        "导出 Markdown",
        data=report.content,
        file_name=f"{selected_grid_id}_选址报告.md",
        mime="text/markdown",
    )


def render(st_module: Any | None = None) -> None:
    """Render the workbench report page."""
    render_report_page(get_streamlit(st_module))
