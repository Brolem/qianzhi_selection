"""Step 9 map-insight page in the Step 11 workbench."""

from __future__ import annotations

from typing import Any

from src.pages.common import get_streamlit
from src.visualization.map_viz import (
    MapProfileSpec,
    available_profile_specs,
    build_profile_map,
)
from src.ui.workbench import render_page_header


def render_map_page(
    st: Any,
    components: Any,
    business_type: str | None = None,
    *,
    profile_specs: dict[str, MapProfileSpec] | None = None,
    map_builder: Any = build_profile_map,
    st_folium_func: Any = None,
    use_workbench_layout: bool = False,
    show_header: bool = True,
) -> None:
    """Render default or custom score maps with the existing fallbacks."""
    if show_header:
        st.header("地图洞察")
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
        "默认｜轻餐饮"
        if business_type == "轻餐饮"
        else "默认｜社区便利店"
    )
    default_index = labels.index(preferred_label) if preferred_label in labels else 0

    def select_spec() -> MapProfileSpec:
        selected_label = st.selectbox(
            "评分方案",
            labels,
            index=default_index,
        )
        return specs[selected_label]

    def render_map(spec: MapProfileSpec) -> None:
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
            st.error("自定义评分方案地图需要安装 streamlit-folium 后动态显示。")
            return
        if not spec.static_html_path.exists():
            st.warning(
                f"缺少输出文件：`{spec.static_html_path}`。"
                "请先运行：`python -m src.visualization.map_viz`"
            )
            return
        components.html(
            spec.static_html_path.read_text(encoding="utf-8"),
            height=680,
            scrolling=True,
        )

    if use_workbench_layout:
        control_panel, map_panel = st.columns([1, 4], gap="large")
        with control_panel:
            with st.container(border=True):
                st.subheader("地图参数")
                spec = select_spec()
                st.caption("浅灰表示未采集，中性灰表示无 POI 活动。")
        with map_panel:
            render_map(spec)
        return

    spec = select_spec()
    render_map(spec)


def render(st_module: Any | None = None) -> None:
    """Render the workbench map page."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "地图洞察",
        "查看 790 个空间网格的数据覆盖状态、相对评分和全局 Top 10。",
    )
    import streamlit.components.v1 as components

    try:
        from streamlit_folium import st_folium
    except ImportError:
        st_folium = None
    render_map_page(
        st,
        components,
        st_folium_func=st_folium,
        use_workbench_layout=True,
        show_header=False,
    )
