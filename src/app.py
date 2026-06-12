"""Streamlit multipage workbench entry point for Qianzhi Selection."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app_legacy import (  # noqa: E402
    business_columns,
    load_table,
    map_file_for_business,
    top_rows,
)
from src.pages import (  # noqa: E402
    data_foundation,
    district_compare,
    grid_recommendation,
    map_insight,
    overview,
    project_notes,
    report_center,
    site_analysis,
)
from src.pages.map_insight import render_map_page  # noqa: E402
from src.pages.report_center import render_report_page  # noqa: E402
from src.ui.workbench import (  # noqa: E402
    apply_workbench_theme,
    render_brand_bar,
)


@dataclass(frozen=True)
class PageRegistration:
    """One stable workbench page registration."""

    title: str
    url_path: str
    renderer: Callable[[], None]
    default: bool = False


PAGE_REGISTRATIONS = [
    PageRegistration("项目总览", "overview", overview.render, default=True),
    PageRegistration("数据底座", "data-foundation", data_foundation.render),
    PageRegistration("选址分析", "site-analysis", site_analysis.render),
    PageRegistration("区域对比", "district-compare", district_compare.render),
    PageRegistration(
        "网格推荐",
        "grid-recommendation",
        grid_recommendation.render,
    ),
    PageRegistration("地图洞察", "map-insight", map_insight.render),
    PageRegistration("智能报告", "report-center", report_center.render),
    PageRegistration("项目说明", "project-notes", project_notes.render),
]


def run_navigation(
    st: Any,
    *,
    registrations: Sequence[PageRegistration] = PAGE_REGISTRATIONS,
) -> None:
    """Run modern Streamlit navigation or the sidebar compatibility path."""
    page_factory = getattr(st, "Page", None)
    navigation = getattr(st, "navigation", None)
    if callable(page_factory) and callable(navigation):
        pages = [
            page_factory(
                registration.renderer,
                title=registration.title,
                url_path=registration.url_path,
                default=registration.default,
            )
            for registration in registrations
        ]
        navigation(
            pages,
            position="sidebar",
            expanded=True,
        ).run()
        return

    by_title = {
        registration.title: registration for registration in registrations
    }
    selected = st.sidebar.radio("页面", list(by_title))
    by_title[selected].renderer()


def main() -> None:
    """Configure and run the Streamlit workbench."""
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit("Please install streamlit before running the app.") from exc
    run_workbench(st)


def run_workbench(st: Any) -> None:
    """Apply the shared shell before running page navigation."""
    st.set_page_config(
        page_title="黔址优选",
        layout="wide",
    )
    apply_workbench_theme(st)
    render_brand_bar(st)
    run_navigation(st)


if __name__ == "__main__":
    main()
