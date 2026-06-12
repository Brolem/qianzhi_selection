"""Stable visual primitives for the Streamlit workbench."""

from __future__ import annotations

from html import escape
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

@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .workbench-metric-grid,
  .workbench-flow {
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

  .workbench-metric-grid,
  .workbench-flow {
    grid-template-columns: minmax(0, 1fr);
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
