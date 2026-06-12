"""Streamlit entry point for Qianzhi Selection.

Run after installing dependencies:
    streamlit run src/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from .config import get_path
    from .reporting.report_generator import generate_site_report
    from .visualization.map_viz import (
        MapProfileSpec,
        available_profile_specs,
        build_profile_map,
    )
except ImportError:
    from src.config import get_path
    from src.reporting.report_generator import generate_site_report
    from src.visualization.map_viz import (
        MapProfileSpec,
        available_profile_specs,
        build_profile_map,
    )


REGION_STAGE_RESULT = get_path("results_region_stage") / "region_stage_score_result.csv"
GRID_STAGE_RESULT = get_path("results_grid_stage") / "grid_stage_score_result.csv"
SELECTED_REGIONS = get_path("results_region_stage") / "selected_regions_for_grid_stage.csv"
OSM_LAYER_INVENTORY = get_path("results_metadata") / "osm_guizhou_layer_inventory.csv"
INDICATOR_TABLE = get_path("results_metadata") / "指标体系表.csv"
WEIGHT_TABLE = get_path("results_metadata") / "权重方案表.csv"
DATA_REASON_REPORT = get_path("reports") / "数据识别与合理性报告.md"
CONVENIENCE_MAP = get_path("figures") / "convenience_grid_map.html"
LIGHT_FOOD_MAP = get_path("figures") / "light_food_grid_map.html"

BUSINESS_TYPES = ["社区便利店", "轻餐饮"]
PAGE_NAMES = [
    "首页",
    "数据概览",
    "指标体系",
    "区域粗筛",
    "网格细筛",
    "地图展示",
    "智能报告",
    "项目说明",
]


def business_columns(business_type: str) -> tuple[str, str]:
    """Return exact score and rank fields for a supported business type."""
    if business_type == "社区便利店":
        return "convenience_score", "rank_convenience"
    if business_type == "轻餐饮":
        return "light_catering_score", "rank_light_catering"
    raise ValueError(f"不支持的业态：{business_type}")


def load_table(path: str | Path) -> pd.DataFrame:
    """Read a CSV table and require the file to exist."""
    table_path = Path(path)
    if not table_path.exists():
        raise FileNotFoundError(f"文件不存在：{table_path}")
    return pd.read_csv(table_path)


def map_file_for_business(business_type: str) -> Path:
    """Return the Step 9 default map HTML path for a supported business type."""
    if business_type == "社区便利店":
        return CONVENIENCE_MAP
    if business_type == "轻餐饮":
        return LIGHT_FOOD_MAP
    raise ValueError(f"不支持的业态：{business_type}")


def top_rows(frame: pd.DataFrame, rank_column: str, limit: int) -> pd.DataFrame:
    """Return top rows sorted by an exact rank column."""
    if rank_column not in frame.columns:
        raise KeyError(f"缺少排序字段：{rank_column}")
    result = frame.copy()
    result[rank_column] = pd.to_numeric(result[rank_column], errors="coerce")
    return result.sort_values(rank_column, ascending=True).head(limit)


def _format_score_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Format score-like columns for Streamlit tables without changing source files."""
    result = frame.copy()
    for column in columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(3)
    return result


def _load_optional_table(path: Path) -> pd.DataFrame | None:
    """Load a table for page rendering; return None when the output is missing."""
    try:
        return load_table(path)
    except FileNotFoundError:
        return None


def _read_optional_text(path: Path) -> str | None:
    """Read a text artifact when it exists."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _missing_output_message(st: Any, path: Path, command: str) -> None:
    """Render a consistent missing-output warning in the app."""
    st.warning(f"缺少输出文件：`{path}`。请先运行：`{command}`")


def _display_dataframe(st: Any, frame: pd.DataFrame, columns: list[str], *, limit: int | None = None) -> None:
    """Display only columns that are present in the provided frame."""
    available = [column for column in columns if column in frame.columns]
    display_frame = frame[available] if available else frame
    if limit is not None:
        display_frame = display_frame.head(limit)
    st.dataframe(display_frame, use_container_width=True)


def render_home(st: Any) -> None:
    """Render the home page."""
    st.title("黔址优选：社区商业智能选址决策系统")
    st.markdown(
        """
        本 Demo 面向社区便利店和轻餐饮早期选址研判，展示从公共数据与 OSM/GIS 数据到两阶段推荐结果的闭环。

        **业务对象**：社区便利店、轻餐饮  
        **推荐对象**：OSM 边界评价区域、1km 评价网格  
        **技术路线**：数据 → 指标 → 评分 → 推荐 → 解释 → 报告 → 演示

        当前结果用于前期筛选和实地调研排序，不替代租金、客流、门店面积和现场竞品复核。
        """
    )

    region_df = _load_optional_table(REGION_STAGE_RESULT)
    grid_df = _load_optional_table(GRID_STAGE_RESULT)
    col1, col2, col3 = st.columns(3)
    col1.metric("区域粗筛记录", 0 if region_df is None else len(region_df))
    col2.metric("1km 评价网格记录", 0 if grid_df is None else len(grid_df))
    col3.metric("支持业态", len(BUSINESS_TYPES))


def render_data_overview(st: Any) -> None:
    """Render source data overview."""
    st.header("数据概览")
    st.markdown(
        """
        官方宏观经济和就业数据用于贵州整体市场背景说明。OSM/GIS 数据用于形成区域和 1km 评价网格之间的空间差异。
        """
    )

    report_text = _read_optional_text(DATA_REASON_REPORT)
    if report_text is None:
        _missing_output_message(st, DATA_REASON_REPORT, "python -m src.data.official_pipeline")
    else:
        st.markdown(report_text)

    inventory_df = _load_optional_table(OSM_LAYER_INVENTORY)
    if inventory_df is None:
        _missing_output_message(st, OSM_LAYER_INVENTORY, "python -m src.osm.inventory")
    else:
        st.subheader("OSM 图层盘点")
        _display_dataframe(
            st,
            inventory_df,
            ["layer_name", "geometry_type", "row_count", "crs", "layer_group", "columns"],
            limit=30,
        )


def render_indicator_system(st: Any) -> None:
    """Render indicators and weights."""
    st.header("指标体系")
    indicator_df = _load_optional_table(INDICATOR_TABLE)
    weight_df = _load_optional_table(WEIGHT_TABLE)

    if indicator_df is None:
        _missing_output_message(st, INDICATOR_TABLE, "python -m src.selection.two_stage --top-n 5 --grid-size-m 1000")
    else:
        st.subheader("五类指标")
        _display_dataframe(st, indicator_df, ["indicator", "meaning", "source_fields", "direction"])

    if weight_df is None:
        _missing_output_message(st, WEIGHT_TABLE, "python -m src.selection.two_stage --top-n 5 --grid-size-m 1000")
    else:
        st.subheader("便利店和轻餐饮权重对比")
        _display_dataframe(st, weight_df, ["indicator", "convenience_store_weight", "light_catering_weight"])

    st.info("竞争压力在评分中通过反向字段参与计算；其余指标为正向支撑。")


def render_region_stage(st: Any, business_type: str) -> None:
    """Render first-stage regional ranking."""
    st.header("区域粗筛")
    region_df = _load_optional_table(REGION_STAGE_RESULT)
    selected_df = _load_optional_table(SELECTED_REGIONS)
    score_col, rank_col = business_columns(business_type)

    if selected_df is not None:
        st.subheader("进入 1km 细筛的区域")
        _display_dataframe(
            st,
            selected_df,
            [
                "selection_rank",
                "region_id",
                "region_name",
                "rank_convenience",
                "rank_light_catering",
                "main_advantage",
                "main_risk",
            ],
        )

    if region_df is None:
        _missing_output_message(st, REGION_STAGE_RESULT, "python -m src.selection.two_stage --top-n 5 --grid-size-m 1000")
        return

    display = _format_score_columns(top_rows(region_df, rank_col, 30), [score_col])
    _display_dataframe(
        st,
        display,
        ["region_id", "region_name", "area_km2", "poi_density", score_col, rank_col, "main_advantage", "main_risk"],
    )


def render_grid_stage(st: Any, business_type: str) -> None:
    """Render second-stage 1km grid ranking."""
    st.header("网格细筛")
    grid_df = _load_optional_table(GRID_STAGE_RESULT)
    score_col, rank_col = business_columns(business_type)

    if grid_df is None:
        _missing_output_message(st, GRID_STAGE_RESULT, "python -m src.selection.two_stage --top-n 5 --grid-size-m 1000")
        return

    filtered = grid_df.copy()
    if "grid_region_name" in filtered.columns:
        region_names = sorted(filtered["grid_region_name"].dropna().astype(str).unique())
        selected_name = st.selectbox("筛选入选区域", ["全部"] + region_names)
        if selected_name != "全部":
            filtered = filtered[filtered["grid_region_name"].astype(str).eq(selected_name)]

    display = _format_score_columns(top_rows(filtered, rank_col, 50), [score_col])
    _display_dataframe(
        st,
        display,
        [
            "grid_id",
            "grid_region_name",
            "centroid_lon",
            "centroid_lat",
            "area_km2",
            score_col,
            rank_col,
            "traffic_accessibility",
            "consumption_potential",
            "synergy_score",
            "competition_pressure",
            "development_basis",
            "main_advantage",
            "main_risk",
        ],
    )


def render_map_page(
    st: Any,
    components: Any,
    business_type: str,
    *,
    profile_specs: dict[str, MapProfileSpec] | None = None,
    map_builder: Any = build_profile_map,
    st_folium_func: Any = None,
) -> None:
    """Render default or custom Step 9 maps without changing other pages."""
    st.header("地图展示")
    try:
        specs = profile_specs or available_profile_specs()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    if not specs:
        st.warning("当前没有可用的评分方案。")
        return

    labels = list(specs)
    preferred_label = (
        "默认｜社区便利店"
        if business_type == "社区便利店"
        else "默认｜轻餐饮"
    )
    default_index = labels.index(preferred_label) if preferred_label in labels else 0
    selected_label = st.selectbox("评分方案", labels, index=default_index)
    spec = specs[selected_label]

    if st_folium_func is not None:
        try:
            result_map = map_builder(spec)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            st.error(str(exc))
            return
        st_folium_func(
            result_map,
            key=f"site_map_{spec.profile_id}",
            height=680,
            use_container_width=True,
        )
        return

    if spec.static_html_path is None:
        st.error(
            "自定义评分方案地图需要安装 streamlit-folium 后动态显示。"
        )
        return
    if not spec.static_html_path.exists():
        _missing_output_message(
            st,
            spec.static_html_path,
            "python -m src.visualization.map_viz",
        )
        return
    components.html(
        spec.static_html_path.read_text(encoding="utf-8"),
        height=680,
        scrolling=True,
    )


def render_report_page(st: Any, business_type: str) -> None:
    """Render template report generation page."""
    st.header("智能报告")
    grid_df = _load_optional_table(GRID_STAGE_RESULT)
    if grid_df is None:
        _missing_output_message(st, GRID_STAGE_RESULT, "python -m src.selection.two_stage --top-n 5 --grid-size-m 1000")
        return

    id_column = "grid_id" if "grid_id" in grid_df.columns else "region_id"
    grid_ids = grid_df[id_column].dropna().astype(str).tolist()
    if not grid_ids:
        st.warning("网格细筛结果为空，无法生成报告。")
        return

    selected_grid_id = st.selectbox("选择 grid_id", grid_ids)
    try:
        report_text = generate_site_report(selected_grid_id, business_type, use_llm=True)
    except (KeyError, FileNotFoundError, ValueError, RuntimeError) as exc:
        st.error(str(exc))
        if not st.button("使用模板报告兜底"):
            return
        report_text = generate_site_report(selected_grid_id, business_type, use_llm=False)

    st.markdown(report_text)
    st.download_button(
        "导出 Markdown",
        data=report_text,
        file_name=f"{selected_grid_id}_{business_type}_选址报告.md",
        mime="text/markdown",
    )


def render_project_notes(st: Any) -> None:
    """Render project limits and next extensions."""
    st.header("项目说明")
    st.markdown(
        """
        **当前限制**

        - 官方宏观经济和就业数据仅用于贵州整体市场背景说明。
        - 当前空间差异来自 OSM POI、道路、土地利用和边界数据。
        - 当前未接入真实租金、实时客流、停车条件、工商信用和门店经营流水数据。

        **决赛数据接入计划**

        - 接入工商、信用、租赁、客流、停车等更细粒度数据后，扩展风险解释和经营建议。
        - 在合法合规的数据条件下补充更高精度的商圈画像和成本约束。

        **后续扩展**

        - 用户自定义权重。
        - 网格面几何地图。
        - Word/PDF 报告导出。
        """
    )


def main() -> None:
    """Run the Streamlit app."""
    try:
        import streamlit as st
        import streamlit.components.v1 as components
    except ImportError as exc:
        raise SystemExit("Please install streamlit before running the app.") from exc
    try:
        from streamlit_folium import st_folium
    except ImportError:
        st_folium = None

    st.set_page_config(page_title="黔址优选", layout="wide")
    page = st.sidebar.radio("页面", PAGE_NAMES)
    business_type = st.sidebar.radio("业态", BUSINESS_TYPES, horizontal=False)

    if page == "首页":
        render_home(st)
    elif page == "数据概览":
        render_data_overview(st)
    elif page == "指标体系":
        render_indicator_system(st)
    elif page == "区域粗筛":
        render_region_stage(st, business_type)
    elif page == "网格细筛":
        render_grid_stage(st, business_type)
    elif page == "地图展示":
        render_map_page(
            st,
            components,
            business_type,
            st_folium_func=st_folium,
        )
    elif page == "智能报告":
        render_report_page(st, business_type)
    elif page == "项目说明":
        render_project_notes(st)


if __name__ == "__main__":
    main()
