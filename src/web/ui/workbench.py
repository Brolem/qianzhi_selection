"""Stable visual primitives for the Streamlit workbench."""

from __future__ import annotations

from html import escape
import re
from typing import Any, Iterable


BRAND_TITLE = "黔址优选 | 社区商业智能选址决策系统"

WORKBENCH_CSS = """
:root {
  --workbench-navy: #132238;
  --workbench-blue: #2563EB;
  --workbench-blue-soft: #EAF1FF;
  --workbench-bg: #F3F5F8;
  --workbench-surface: #FFFFFF;
  --workbench-border: #DDE3EA;
  --workbench-text: #172033;
  --workbench-muted: #64748B;
  --workbench-success: #176B4A;
  --workbench-warning: #A16207;
  --workbench-danger: #B42318;
}

[data-testid="stApp"] {
  background: var(--workbench-bg);
  color: var(--workbench-text);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
    Arial, sans-serif;
}

[data-testid="stMainBlockContainer"] {
  max-width: 1540px;
  padding-top: 4rem;
  padding-bottom: 2rem;
}

[data-testid="stSidebar"] {
  background: var(--workbench-surface);
  border-right: 1px solid var(--workbench-border);
}

[data-testid="stSidebarNavLink"] {
  min-height: 2.5rem;
  border-left: 3px solid transparent;
  border-radius: 0 4px 4px 0;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
  color: var(--workbench-blue);
  background: var(--workbench-blue-soft);
  border-left-color: var(--workbench-blue);
  font-weight: 600;
}

[data-testid="stMetric"],
[data-testid="stDataFrame"],
[data-testid="stAlert"],
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--workbench-surface);
  border-color: var(--workbench-border);
  border-radius: 6px;
}

[data-testid="stDataFrame"] {
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(19, 34, 56, 0.06);
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  border-color: var(--workbench-border);
  border-radius: 5px;
}

.stButton > button,
.stDownloadButton > button {
  border-radius: 5px;
  border-color: var(--workbench-blue);
}

.stButton > button[kind="primary"] {
  background: var(--workbench-blue);
}

.workbench-brand-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  padding: 0 20px;
  margin: 0 0 18px;
  color: #FFFFFF;
  background: var(--workbench-navy);
  border-left: 4px solid var(--workbench-blue);
  border-radius: 6px;
  font-size: 24px;
  text-align: center;
  font-weight: 700;
  line-height: 1.4;
}

.workbench-page-header {
  margin: 0 0 16px;
}

.workbench-page-header h1 {
  margin: 0;
  color: var(--workbench-text);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: 0;
}

.workbench-page-header p {
  margin: 6px 0 0;
  color: var(--workbench-muted);
  font-size: 14px;
  line-height: 1.7;
}

.workbench-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 14px 0 16px;
}

.workbench-metric-card {
  min-width: 0;
  padding: 15px 16px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-top: 3px solid var(--workbench-blue);
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(19, 34, 56, 0.07);
}

.workbench-metric-label {
  color: var(--workbench-muted);
  font-size: 13px;
  line-height: 1.4;
}

.workbench-metric-value {
  margin-top: 6px;
  color: var(--workbench-text);
  font-size: 25px;
  font-weight: 700;
  line-height: 1.15;
}

.workbench-metric-note {
  margin-top: 6px;
  color: var(--workbench-muted);
  font-size: 12px;
  line-height: 1.5;
}

.workbench-flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 4px 0 18px;
}

.workbench-flow-step {
  min-width: 0;
  padding: 12px 14px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-radius: 6px;
}

.workbench-flow-step.is-active {
  color: var(--workbench-blue);
  background: var(--workbench-blue-soft);
  border-color: var(--workbench-blue);
}

.workbench-flow-index {
  display: block;
  margin-bottom: 4px;
  color: var(--workbench-muted);
  font-size: 12px;
  font-weight: 600;
}

.workbench-flow-step.is-active .workbench-flow-index {
  color: var(--workbench-blue);
}

.workbench-flow-label {
  display: block;
  overflow-wrap: anywhere;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
}

.workbench-secondary-note {
  margin: 0 0 14px;
  color: var(--workbench-muted);
  font-size: 13px;
  line-height: 1.6;
}

.workbench-inline-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 16px;
  min-height: 28px;
  margin: 4px 0 8px;
  color: var(--workbench-muted);
  font-size: 12px;
  line-height: 1.4;
}

.workbench-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.workbench-legend-swatch {
  width: 10px;
  height: 10px;
  flex: 0 0 10px;
  border-radius: 2px;
}

.workbench-decision-summary {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 225px;
  padding: 4px 2px 2px;
}

.workbench-decision-label {
  color: var(--workbench-muted);
  font-size: 13px;
  font-weight: 600;
}

.workbench-decision-score {
  display: flex;
  align-items: baseline;
  flex-wrap: nowrap;
  margin: 10px 0 18px;
  color: var(--workbench-text);
  font-size: 46px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.workbench-decision-score small {
  flex: 0 0 auto;
  margin-left: 4px;
  color: var(--workbench-muted);
  font-size: 14px;
  font-weight: 500;
}

.workbench-decision-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--workbench-border);
}

.workbench-rank {
  color: var(--workbench-text);
  font-size: 15px;
  font-weight: 600;
}

.workbench-status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.workbench-status-badge.is-success {
  color: #0F5132;
  background: #DDF3E8;
}

.workbench-status-badge.is-warning {
  color: #7A4D00;
  background: #FFF0C2;
}

.workbench-status-badge.is-neutral {
  color: #475569;
  background: #E9EDF2;
}

.workbench-coverage-funnel {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  align-items: stretch;
  gap: 10px;
  margin: 4px 0 18px;
}

.workbench-coverage-stage {
  padding: 12px 14px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-radius: 6px;
}

.workbench-coverage-stage.is-active {
  background: #EEF8F3;
  border-color: #9CCFBA;
}

.workbench-coverage-label {
  color: var(--workbench-muted);
  font-size: 12px;
}

.workbench-coverage-value {
  margin-top: 3px;
  color: var(--workbench-text);
  font-size: 22px;
  font-weight: 700;
}

.workbench-coverage-note {
  margin-top: 3px;
  color: var(--workbench-muted);
  font-size: 11px;
}

.workbench-coverage-arrow {
  display: flex;
  align-items: center;
  color: #94A3B8;
  font-size: 18px;
}

.workbench-report-preview {
  padding: 14px 16px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-radius: 6px;
}

.workbench-report-preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--workbench-border);
}

.workbench-report-preview-score {
  color: var(--workbench-text);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}

.workbench-report-preview-score small {
  color: var(--workbench-muted);
  font-size: 12px;
  font-weight: 500;
}

.workbench-report-preview-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.workbench-report-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 14px;
  margin-top: 12px;
}

.workbench-report-preview-row {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 8px;
  color: var(--workbench-muted);
  font-size: 12px;
}

.workbench-report-preview-track {
  height: 6px;
  overflow: hidden;
  background: #E7ECF2;
  border-radius: 999px;
}

.workbench-report-preview-fill {
  display: block;
  height: 100%;
  background: var(--workbench-blue);
  border-radius: inherit;
}

.workbench-budget-panel {
  margin: 12px 0 16px;
  padding: 13px 15px 12px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(19, 34, 56, 0.05);
}

.workbench-budget-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--workbench-muted);
  font-size: 12px;
  line-height: 1.4;
}

.workbench-budget-heading strong {
  color: var(--workbench-text);
  font-size: 13px;
  font-weight: 700;
}

.workbench-budget-track {
  height: 7px;
  margin: 9px 0 12px;
  overflow: hidden;
  background: #E7ECF2;
  border-radius: 999px;
}

.workbench-budget-progress {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--workbench-blue);
}

.workbench-budget-progress.is-complete {
  background: var(--workbench-success);
}

.workbench-budget-progress.is-over {
  background: var(--workbench-danger);
}

.workbench-budget-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.workbench-budget-item {
  min-width: 0;
  padding: 8px 10px;
  background: #F7F9FC;
  border-left: 3px solid #AFC4EE;
  border-radius: 4px;
}

.workbench-budget-item.is-ready {
  background: #EEF8F3;
  border-left-color: var(--workbench-success);
}

.workbench-budget-item.is-over {
  background: #FEF1F0;
  border-left-color: var(--workbench-danger);
}

.workbench-budget-label {
  display: block;
  color: var(--workbench-muted);
  font-size: 11px;
  line-height: 1.35;
}

.workbench-budget-value {
  display: block;
  margin-top: 2px;
  color: var(--workbench-text);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
}

.workbench-budget-value.is-text {
  font-size: 17px;
}

.workbench-diagnostic-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin: 10px 0 14px;
}

.workbench-diagnostic-card {
  min-width: 0;
  padding: 9px 11px;
  background: var(--workbench-surface);
  border: 1px solid var(--workbench-border);
  border-left: 4px solid #94A3B8;
  border-radius: 5px;
}

.workbench-diagnostic-card.is-gap {
  background: #EDF8F3;
  border-left-color: #23855F;
}

.workbench-diagnostic-card.is-cultivation {
  background: #FFF8E8;
  border-left-color: #C58A18;
}

.workbench-diagnostic-card.is-mature {
  background: #EBF2FC;
  border-left-color: #326FC2;
}

.workbench-diagnostic-card.is-general {
  background: #F2F4F7;
  border-left-color: #7A8798;
}

.workbench-diagnostic-card.is-alert {
  background: #FEF0EF;
  border-left-color: #C2443A;
}

.workbench-diagnostic-label {
  display: block;
  overflow-wrap: anywhere;
  color: var(--workbench-muted);
  font-size: 11px;
  line-height: 1.35;
}

.workbench-diagnostic-value {
  display: block;
  margin-top: 3px;
  color: var(--workbench-text);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
}

.st-key-report-content [data-testid="stMarkdownContainer"] {
  color: var(--workbench-text);
  font-size: 15px;
  line-height: 1.75;
}

.st-key-report-content [data-testid="stMarkdownContainer"] h1 {
  margin: 1.35rem 0 0.65rem;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.4;
}

.st-key-report-content [data-testid="stMarkdownContainer"] h2 {
  margin: 1.2rem 0 0.6rem;
  font-size: 20px;
  line-height: 1.45;
}

.st-key-report-content [data-testid="stMarkdownContainer"] h3 {
  margin: 1rem 0 0.5rem;
  font-size: 17px;
  line-height: 1.5;
}

.st-key-report-content [data-testid="stMarkdownContainer"] p,
.st-key-report-content [data-testid="stMarkdownContainer"] li {
  font-size: 15px;
  line-height: 1.75;
}

.st-key-report-content [data-testid="stMarkdownContainer"] ul,
.st-key-report-content [data-testid="stMarkdownContainer"] ol {
  margin-bottom: 0.8rem;
  padding-left: 1.35rem;
}

@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .workbench-metric-grid,
  .workbench-flow,
  .workbench-diagnostic-grid,
  .workbench-report-preview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
  }

  [data-testid="column"] {
    flex: 1 1 100% !important;
    width: 100%;
    min-width: 100%;
  }
}

@media (max-width: 600px) {
  .workbench-brand-bar {
    min-height: 54px;
    padding: 6px 10px;
    font-size: 16px;
    line-height: 1.25;
  }

  .workbench-page-header h1 {
    font-size: 22px;
  }

  .st-key-report-content [data-testid="stMarkdownContainer"] h1 {
    font-size: 21px;
  }

  .st-key-report-content [data-testid="stMarkdownContainer"] h2 {
    font-size: 18px;
  }

  .st-key-report-content [data-testid="stMarkdownContainer"],
  .st-key-report-content [data-testid="stMarkdownContainer"] p,
  .st-key-report-content [data-testid="stMarkdownContainer"] li {
    font-size: 14px;
  }

  .workbench-metric-grid,
  .workbench-flow,
  .workbench-diagnostic-grid,
  .workbench-budget-summary,
  .workbench-report-preview-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .workbench-coverage-funnel {
    grid-template-columns: minmax(0, 1fr);
  }

  .workbench-coverage-arrow {
    justify-content: center;
    transform: rotate(90deg);
  }

  [data-testid="stHorizontalBlock"] {
    display: block;
  }

  [data-testid="column"] {
    width: 100%;
    min-width: 100%;
  }
}
""".strip()


def _render_html(st: Any, body: str) -> None:
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(body)
        return
    st.markdown(body, unsafe_allow_html=True)


def render_html(st: Any, body: str) -> None:
    """Render trusted project HTML through the available Streamlit API."""
    _render_html(st, body)


def apply_workbench_theme(st: Any) -> None:
    """Inject the shared workbench CSS without external assets."""
    _render_html(st, f"<style>{WORKBENCH_CSS}</style>")


def render_brand_bar(st: Any) -> None:
    """Render the normal-flow product title bar."""
    _render_html(
        st,
        f'<div class="workbench-brand-bar">{escape(BRAND_TITLE)}</div>',
    )


def render_page_header(st: Any, title: str, description: str) -> None:
    """Render one consistent page heading with escaped dynamic text."""
    _render_html(
        st,
        (
            '<section class="workbench-page-header">'
            f"<h1>{escape(str(title))}</h1>"
            f"<p>{escape(str(description))}</p>"
            "</section>"
        ),
    )


def render_metric_cards(
    st: Any,
    metrics: Iterable[tuple[str, object, str]],
) -> None:
    """Render a stable four-column metric grid."""
    cards = []
    for label, value, note in metrics:
        cards.append(
            '<article class="workbench-metric-card">'
            f'<div class="workbench-metric-label">{escape(str(label))}</div>'
            f'<div class="workbench-metric-value">{escape(str(value))}</div>'
            f'<div class="workbench-metric-note">{escape(str(note))}</div>'
            "</article>"
        )
    _render_html(
        st,
        '<section class="workbench-metric-grid">'
        + "".join(cards)
        + "</section>",
    )


def render_inline_legend(
    st: Any,
    items: Iterable[tuple[str, str]],
) -> None:
    """Render one stable horizontal legend with equal-size swatches."""
    entries = []
    for label, color in items:
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
            raise ValueError(f"图例颜色必须是六位十六进制颜色：{color}")
        entries.append(
            '<span class="workbench-legend-item">'
            '<span class="workbench-legend-swatch" '
            f'style="background:{color}"></span>'
            f"<span>{escape(str(label))}</span>"
            "</span>"
        )
    _render_html(
        st,
        '<div class="workbench-inline-legend">'
        + "".join(entries)
        + "</div>",
    )


def render_workflow_steps(st: Any, active_step: int = 3) -> None:
    """Render the four-step static site-selection process."""
    if active_step not in {1, 2, 3, 4}:
        raise ValueError("active_step 必须为 1、2、3 或 4")
    labels = [
        "选择应用场景",
        "设置分析参数",
        "查看推荐结果",
        "生成报告",
    ]
    steps = []
    for index, label in enumerate(labels, start=1):
        active_class = " is-active" if index == active_step else ""
        steps.append(
            f'<article class="workbench-flow-step{active_class}" '
            f'data-step="{index}">'
            f'<span class="workbench-flow-index">STEP {index}</span>'
            f'<span class="workbench-flow-label">{escape(label)}</span>'
            "</article>"
        )
    _render_html(
        st,
        '<section class="workbench-flow">' + "".join(steps) + "</section>",
    )
