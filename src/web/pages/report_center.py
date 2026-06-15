"""Step 10 report center in the Step 11 workbench."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd

from src.web.pages.common import get_streamlit
from src.presentation.report_generator import (
    active_profile_results,
    generate_site_report,
)
from src.presentation.map_viz import MapProfileSpec, available_profile_specs
from src.web.ui.workbench import render_page_header
from src.web.ui.workbench import render_html
from src.web.decision_context import (
    grid_default_index,
    profile_default_index,
    save_decision_context,
)


def build_report_preview(
    frame: pd.DataFrame,
    profile: MapProfileSpec,
    grid_id: str,
) -> dict[str, Any]:
    """Build a program-generated report preview for one ranked grid."""
    required = [
        "grid_id",
        "district_name",
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        profile.synergy_field,
        profile.competition_score_field,
        profile.score_field,
        profile.rank_field,
        profile.district_rank_field,
        profile.level_field,
        profile.market_stage_field,
        profile.competition_alert_field,
        profile.advantage_field,
        profile.risk_field,
    ]
    missing = [field for field in required if field not in frame]
    if missing:
        raise KeyError("评分结果缺少字段：" + ", ".join(missing))
    selected = frame.loc[frame["grid_id"].astype(str).eq(str(grid_id))]
    if len(selected) != 1:
        raise ValueError(f"评价网格必须唯一存在：{grid_id}")
    row = selected.iloc[0]
    metrics = pd.DataFrame(
        [
            ("交通可达性", row["traffic_accessibility"]),
            ("消费潜力", row["consumption_potential"]),
            ("就业客群代理", row["employment_customer_proxy"]),
            ("共生业态", row[profile.synergy_field]),
            ("低竞争得分", row[profile.competition_score_field]),
            ("商业氛围", row["business_atmosphere"]),
        ],
        columns=["指标", "得分"],
    )
    metrics["得分"] = pd.to_numeric(metrics["得分"], errors="raise")
    return {
        "grid_id": str(row["grid_id"]),
        "district_name": str(row["district_name"]),
        "score": float(row[profile.score_field]),
        "rank": int(float(row[profile.rank_field])),
        "district_rank": int(float(row[profile.district_rank_field])),
        "level": str(row[profile.level_field]),
        "market_stage": str(row[profile.market_stage_field]),
        "competition_alert": str(row[profile.competition_alert_field]),
        "advantage": str(row[profile.advantage_field]),
        "risk": str(row[profile.risk_field]),
        "metrics": metrics,
    }


def _report_preview_html(preview: dict[str, Any]) -> str:
    """Render one compact decision preview before invoking DeepSeek."""
    alert_class = (
        "is-warning"
        if preview["competition_alert"] == "过度竞争预警"
        else "is-neutral"
    )
    rows = []
    for _, metric in preview["metrics"].iterrows():
        score = max(0.0, min(float(metric["得分"]), 100.0))
        rows.append(
            '<div class="workbench-report-preview-row">'
            f"<span>{escape(str(metric['指标']))}</span>"
            '<span class="workbench-report-preview-track">'
            f'<span class="workbench-report-preview-fill" style="width:{score:.1f}%"></span>'
            "</span>"
            f"<strong>{score:.1f}</strong>"
            "</div>"
        )
    return (
        '<section class="workbench-report-preview">'
        '<div class="workbench-report-preview-head">'
        "<div>"
        f'<div class="workbench-report-preview-score">{preview["score"]:.2f}'
        "<small> / 100</small></div>"
        f'<div class="workbench-metric-note">{escape(preview["district_name"])}'
        f'｜全局 #{preview["rank"]}｜区内 #{preview["district_rank"]}</div>'
        "</div>"
        '<div class="workbench-report-preview-meta">'
        f'<span class="workbench-status-badge is-success">{escape(preview["level"])}</span>'
        f'<span class="workbench-status-badge is-neutral">{escape(preview["market_stage"])}</span>'
        f'<span class="workbench-status-badge {alert_class}">{escape(preview["competition_alert"])}</span>'
        "</div></div>"
        '<div class="workbench-report-preview-grid">'
        + "".join(rows)
        + "</div>"
        f'<div class="workbench-metric-note">优势：{escape(preview["advantage"])}；'
        f'风险：{escape(preview["risk"])}</div>'
        "</section>"
    )


def render_report_page(
    st: Any,
    business_type: str | None = None,
    *,
    profile_specs: dict[str, MapProfileSpec] | None = None,
    report_generator_func: Any = generate_site_report,
    use_workbench_layout: bool = False,
    show_header: bool = True,
) -> None:
    """Render button-triggered default or custom DeepSeek reports."""
    del business_type
    if show_header:
        st.header("智能报告")
    try:
        specs = profile_specs or available_profile_specs()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    if not specs:
        st.warning("没有可用的评分方案。")
        return

    def select_target() -> tuple[MapProfileSpec, str, dict[str, Any]] | None:
        profile_index = profile_default_index(specs, st.session_state)
        selected_label = st.selectbox(
            "评分方案",
            list(specs),
            index=profile_index,
        )
        profile = specs[selected_label]
        try:
            active = active_profile_results(profile)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            st.error(str(exc))
            return None
        if active.empty:
            st.warning("该评分方案没有可用于生成报告的活跃排名网格。")
            return None

        option_to_grid: dict[str, str] = {}
        for _, row in active.iterrows():
            rank = int(float(row[profile.rank_field]))
            score = float(row[profile.score_field])
            grid_id = str(row["grid_id"])
            label = (
                f"#{rank}｜{row['district_name']}｜{grid_id}｜{score:.2f}分"
            )
            option_to_grid[label] = grid_id
        selected_grid_label = st.selectbox(
            "评价网格",
            list(option_to_grid),
            index=grid_default_index(active, st.session_state),
        )
        selected_grid_id = option_to_grid[selected_grid_label]
        save_decision_context(
            st.session_state,
            profile_id=profile.profile_id,
            grid_id=selected_grid_id,
        )
        return (
            profile,
            selected_grid_id,
            build_report_preview(active, profile, selected_grid_id),
        )

    def generate_report(
        profile: MapProfileSpec,
        selected_grid_id: str,
        *,
        use_llm: bool,
    ) -> None:
        state_prefix = (
            f"site_report:{profile.profile_id}:{selected_grid_id}"
        )
        result_key = f"{state_prefix}:result"
        error_key = f"{state_prefix}:error"
        running_label = (
            "正在生成智能报告，通常需要数秒，请勿重复点击。"
            if use_llm
            else "正在生成模板报告。"
        )
        complete_label = (
            "智能报告生成完成。"
            if use_llm
            else "模板报告生成完成。"
        )
        failed_label = (
            "智能报告生成失败。"
            if use_llm
            else "模板报告生成失败。"
        )
        with st.status(
            running_label,
            expanded=True,
            state="running",
        ) as generation_status:
            try:
                st.session_state[result_key] = report_generator_func(
                    selected_grid_id,
                    profile,
                    use_llm=use_llm,
                )
                st.session_state.pop(error_key, None)
            except Exception as exc:
                st.session_state.pop(result_key, None)
                st.session_state[error_key] = str(exc)
                generation_status.update(
                    label=failed_label,
                    state="error",
                    expanded=True,
                )
            else:
                generation_status.update(
                    label=complete_label,
                    state="complete",
                    expanded=False,
                )

    def render_report_state(
        profile: MapProfileSpec,
        selected_grid_id: str,
        preview: dict[str, Any],
        *,
        show_empty: bool,
    ) -> None:
        state_prefix = (
            f"site_report:{profile.profile_id}:{selected_grid_id}"
        )
        result_key = f"{state_prefix}:result"
        error_key = f"{state_prefix}:error"
        if error_key in st.session_state:
            st.error(st.session_state[error_key])
            if st.button("使用模板报告"):
                generate_report(
                    profile,
                    selected_grid_id,
                    use_llm=False,
                )

        report = st.session_state.get(result_key)
        if report is None:
            if show_empty:
                render_html(st, _report_preview_html(preview))
                st.info("选择评分方案和评价网格后，点击“生成智能报告”。")
            return
        if report.mode == "template":
            st.info("当前展示规则模板报告。")
        elif report.used_fallback:
            st.info(
                f"DeepSeek 模型：{report.model}（Pro 暂不可用，已回退）。"
            )
        else:
            st.info(f"DeepSeek 模型：{report.model}。")
        with st.container(key="report-content"):
            st.markdown(report.content)
        st.download_button(
            "导出 Markdown",
            data=report.content,
            file_name=f"{selected_grid_id}_选址报告.md",
            mime="text/markdown",
        )

    if use_workbench_layout:
        control_panel, report_panel = st.columns([1, 2.4], gap="large")
        with control_panel:
            with st.container(border=True):
                st.subheader("报告参数")
                target = select_target()
                if target is not None and st.button("生成智能报告"):
                    generate_report(target[0], target[1], use_llm=True)
        if target is None:
            return
        with report_panel:
            with st.container(border=True):
                st.subheader("报告结果")
                render_report_state(*target, show_empty=True)
        return

    target = select_target()
    if target is None:
        return
    if st.button("生成智能报告"):
        generate_report(target[0], target[1], use_llm=True)
    render_report_state(*target, show_empty=False)


def render(st_module: Any | None = None) -> None:
    """Render the workbench report page."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "智能报告",
        "为具备 POI 活动和有效排名的网格生成结构化选址研判报告。",
    )
    render_report_page(
        st,
        use_workbench_layout=True,
        show_header=False,
    )
