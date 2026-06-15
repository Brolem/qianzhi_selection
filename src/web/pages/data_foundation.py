"""Data-foundation page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.web.pages.common import (
    EMPLOYMENT_PATH,
    MACRO_PATH,
    POI_COUNTS_PATH,
    SCORING_INPUT_PATH,
    SPATIAL_GRIDS_PATH,
    TARGET_DISTRICTS_PATH,
    get_streamlit,
    load_required_csv,
)
from src.web.ui.workbench import render_page_header


def _foundation_row(
    path: str | Path,
    required_columns: list[str],
    data_name: str,
    geographic_scope: str,
    data_role: str,
    coordinate_note: str,
) -> dict[str, Any]:
    frame = load_required_csv(path, required_columns)
    return {
        "data_name": data_name,
        "record_count": len(frame),
        "geographic_scope": geographic_scope,
        "data_role": data_role,
        "coordinate_note": coordinate_note,
    }


def build_data_foundation_rows(
    *,
    districts_path: str | Path = TARGET_DISTRICTS_PATH,
    poi_counts_path: str | Path = POI_COUNTS_PATH,
    macro_path: str | Path = MACRO_PATH,
    employment_path: str | Path = EMPLOYMENT_PATH,
    grids_path: str | Path | None = None,
    scoring_input_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Build auditable descriptions for the current v2 data foundation."""
    rows = [
        _foundation_row(
            districts_path,
            ["district_name", "adcode", "data_source"],
            "目标区县基础信息",
            "贵阳市三个目标区县",
            "区县边界与空间约束",
            "高德原始坐标为 GCJ-02",
        ),
        _foundation_row(
            poi_counts_path,
            ["grid_id", "district_name"],
            "网格 POI 统计",
            "贵阳市三个目标区县的 60 个样本网格",
            "网格指标工程的 POI 样本输入",
            "采用统一 500 米周边查询口径",
        ),
        _foundation_row(
            macro_path,
            ["area_code", "index_name", "value"],
            "官方宏观数据",
            "贵州省级背景",
            "市场背景与数据边界说明",
            "不拆分到区县或网格",
        ),
        _foundation_row(
            employment_path,
            ["region_id", "region_name"],
            "官方就业数据",
            "贵州省级背景",
            "就业背景与数据边界说明",
            "不进入网格评分",
        ),
    ]
    if grids_path is not None:
        rows.insert(
            1,
            _foundation_row(
                grids_path,
                ["grid_id", "district_name", "data_source"],
                "1km 空间网格",
                "贵阳市三个目标区县的完整研究范围",
                "评分对象与地图空间底板",
                "高德地图使用 GCJ-02 原始坐标；兼容地图显示时转换为 WGS84",
            ),
        )
    if scoring_input_path is not None:
        rows.insert(
            -2,
            _foundation_row(
                scoring_input_path,
                ["grid_id", "district_name", "has_poi_activity"],
                "网格评分输入",
                "贵阳市三个目标区县的 60 个样本网格",
                "六维指标和评分审计输入",
                "仅包含已采集样本网格",
            ),
        )
    return rows


def format_data_foundation_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Return the data inventory with presentation-safe Chinese headings."""
    return pd.DataFrame(rows).rename(
        columns={
            "data_name": "数据资产",
            "record_count": "记录数",
            "geographic_scope": "地域范围",
            "data_role": "数据角色",
            "coordinate_note": "坐标与口径",
        }
    )[
        ["数据资产", "记录数", "地域范围", "数据角色", "坐标与口径"]
    ]


def render(st_module: Any | None = None) -> None:
    """Render the current data-foundation inventory."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "数据底座",
        "核对当前真实文件、记录规模、地域范围、数据角色和坐标口径。",
    )
    try:
        rows = build_data_foundation_rows(
            grids_path=SPATIAL_GRIDS_PATH,
            scoring_input_path=SCORING_INPUT_PATH,
        )
    except (FileNotFoundError, KeyError) as exc:
        st.error(str(exc))
        return
    with st.container(border=True):
        st.subheader("当前数据资产")
        st.dataframe(
            format_data_foundation_table(rows),
            use_container_width=True,
            hide_index=True,
        )
    st.info(
        "官方数据当前只提供贵州省级背景；网格空间差异来自高德区县边界、"
        "POI 样本和统一指标工程。"
    )
