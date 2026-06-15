"""District background comparison page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd

from src.web.pages.common import (
    DISTRICT_SUMMARY_PATH,
    POI_COUNTS_PATH,
    get_streamlit,
    load_required_csv,
)
from src.web.ui.workbench import render_page_header


DISTRICT_SUMMARY_FIELDS = [
    "district_name",
    "grid_count",
    "active_grid_count",
    "poi_total_count",
    "avg_convenience_score",
    "top_convenience_grid_id",
    "avg_light_food_score",
    "top_light_food_grid_id",
]

POI_COMPARISON_GROUPS = {
    "主力业态": {
        "convenience_store": "便利店",
        "restaurant": "餐饮",
    },
    "客群与商业设施": {
        "school": "学校",
        "hospital": "医院",
        "mall": "商场",
        "office": "写字楼",
        "residential": "小区",
    },
    "交通设施": {
        "bus_stop": "公交站",
        "subway_station": "地铁站",
        "parking": "停车场",
    },
}


def load_district_comparison(
    path: str | Path = DISTRICT_SUMMARY_PATH,
):
    """Load the Step 8 district grouping summary."""
    return load_required_csv(path, DISTRICT_SUMMARY_FIELDS)[
        DISTRICT_SUMMARY_FIELDS
    ].copy()


def format_district_summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the district summary with Chinese display headings."""
    result = frame[DISTRICT_SUMMARY_FIELDS].copy()
    for field in ["avg_convenience_score", "avg_light_food_score"]:
        result[field] = pd.to_numeric(result[field], errors="coerce").round(2)
    return result.rename(
        columns={
            "district_name": "区县",
            "grid_count": "网格数",
            "active_grid_count": "活跃网格数",
            "poi_total_count": "POI 总量",
            "avg_convenience_score": "便利店平均分",
            "top_convenience_grid_id": "便利店最高分网格",
            "avg_light_food_score": "轻餐饮平均分",
            "top_light_food_grid_id": "轻餐饮最高分网格",
        }
    )


def build_district_poi_comparison(
    path: str | Path = POI_COUNTS_PATH,
) -> pd.DataFrame:
    """Aggregate selected raw POI counts by district and display group."""
    category_map = {
        category: label
        for categories in POI_COMPARISON_GROUPS.values()
        for category, label in categories.items()
    }
    group_map = {
        category: group
        for group, categories in POI_COMPARISON_GROUPS.items()
        for category in categories
    }
    count_fields = [f"{category}_count" for category in category_map]
    frame = load_required_csv(path, ["district_name", *count_fields])
    numeric = frame[count_fields].apply(pd.to_numeric, errors="coerce")
    invalid = numeric.isna() & frame[count_fields].notna()
    if invalid.any().any():
        field = invalid.any(axis=0).loc[lambda value: value].index[0]
        raise ValueError(f"{path} 的 {field} 包含非数字值")
    numeric = numeric.fillna(0)
    if (numeric < 0).any().any():
        field = (numeric < 0).any(axis=0).loc[lambda value: value].index[0]
        raise ValueError(f"{path} 的 {field} 包含负数")
    grouped = pd.concat(
        [frame[["district_name"]].astype(str), numeric],
        axis=1,
    ).groupby("district_name", as_index=False, sort=True)[count_fields].sum()
    result = grouped.melt(
        id_vars="district_name",
        value_vars=count_fields,
        var_name="count_field",
        value_name="poi_count",
    )
    result["poi_category"] = result["count_field"].str.removesuffix("_count")
    result["poi_label"] = result["poi_category"].map(category_map)
    result["category_group"] = result["poi_category"].map(group_map)
    return result[
        [
            "district_name",
            "category_group",
            "poi_category",
            "poi_label",
            "poi_count",
        ]
    ]


def _grouped_bar_chart(
    frame: pd.DataFrame,
    group: str,
    *,
    show_legend: bool = True,
    height: int = 230,
) -> alt.Chart:
    data = frame.loc[frame["category_group"].eq(group)].copy()
    legend = (
        alt.Legend(
            title=None,
            orient="top",
            direction="horizontal",
        )
        if show_legend
        else None
    )
    return (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "poi_label:N",
                title=None,
                sort=list(POI_COMPARISON_GROUPS[group].values()),
                axis=alt.Axis(
                    labelAngle=360,
                    labelPadding=8,
                    labelLimit=90,
                ),
            ),
            xOffset=alt.XOffset("district_name:N"),
            y=alt.Y("poi_count:Q", title="原始 POI 数量"),
            color=alt.Color(
                "district_name:N",
                title="区县",
                scale=alt.Scale(
                    range=["#176B4A", "#2F6FBE", "#D98252"],
                ),
                legend=legend,
            ),
            tooltip=[
                alt.Tooltip("district_name:N", title="区县"),
                alt.Tooltip("poi_label:N", title="POI 类别"),
                alt.Tooltip("poi_count:Q", title="原始数量", format=",.0f"),
            ],
        )
        .properties(height=height)
    )


def render(st_module: Any | None = None) -> None:
    """Render district grouping context without replacing grid ranking."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "区域对比",
        "对比三区网格规模、活跃样本、POI 总量和两类默认方案表现。",
    )
    try:
        frame = load_district_comparison()
        poi_frame = build_district_poi_comparison()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    with st.container(border=True):
        st.subheader("三区汇总")
        st.dataframe(
            format_district_summary_table(frame),
            use_container_width=True,
            hide_index=True,
        )
    st.subheader("区县 POI 原始数量对比")
    business_column, transport_column = st.columns(2, gap="large")
    with business_column:
        st.markdown("**便利店与餐饮**")
        st.altair_chart(
            _grouped_bar_chart(poi_frame, "主力业态"),
            width="stretch",
        )
    with transport_column:
        st.markdown("**交通设施**")
        st.altair_chart(
            _grouped_bar_chart(
                poi_frame,
                "交通设施",
                show_legend=False,
            ),
            width="stretch",
        )
    st.markdown("**客群与商业设施**")
    st.altair_chart(
        _grouped_bar_chart(
            poi_frame,
            "客群与商业设施",
            show_legend=False,
            height=260,
        ),
        width="stretch",
    )
    st.info(
        "图表展示 60 个已采集网格的原始 POI 数量。区县对比仅用于"
        "背景画像和结果分组，最终推荐仍以 1km 评价网格评分为准。"
    )
