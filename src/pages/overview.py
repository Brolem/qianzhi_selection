"""Project overview page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd

from src.pages.common import (
    POI_COUNTS_PATH,
    SCORES_PATH,
    SPATIAL_GRIDS_PATH,
    TARGET_DISTRICTS_PATH,
    activity_mask,
    get_streamlit,
    load_profile_options,
    load_required_csv,
)
from src.config import get_poi_categories
from src.profile_catalog import ResultProfileSpec
from src.ui.workbench import (
    render_metric_cards,
    render_page_header,
)

POI_THEME_GROUPS = {
    "community_retail": {
        "label": "社区零售",
        "categories": ["convenience_store", "supermarket"],
    },
    "food_consumption": {
        "label": "餐饮消费",
        "categories": ["restaurant", "fast_food", "snack", "cafe", "tea"],
    },
    "daily_customer": {
        "label": "生活客群",
        "categories": ["school", "hospital", "residential"],
    },
    "business_office": {
        "label": "商业办公",
        "categories": ["mall", "office"],
    },
    "transport_support": {
        "label": "交通配套",
        "categories": ["bus_stop", "subway_station", "parking"],
    },
}


def load_overview_metrics(
    *,
    districts_path: str | Path = TARGET_DISTRICTS_PATH,
    grids_path: str | Path = SPATIAL_GRIDS_PATH,
    poi_counts_path: str | Path = POI_COUNTS_PATH,
    scores_path: str | Path = SCORES_PATH,
    profile_specs: dict[str, ResultProfileSpec] | None = None,
    poi_categories: dict[str, str] | None = None,
) -> dict[str, int]:
    """Load the five workbench scope indicators from v2 outputs."""
    districts = load_required_csv(districts_path, ["district_name"])
    grids = load_required_csv(grids_path, ["grid_id"])
    poi_counts = load_required_csv(poi_counts_path, ["grid_id"])
    scores = load_required_csv(
        scores_path,
        ["grid_id", "has_poi_activity"],
    )
    specs = load_profile_options(profile_specs)
    categories = (
        poi_categories
        if poi_categories is not None
        else get_poi_categories()
    )
    return {
        "district_count": len(districts),
        "spatial_grid_count": len(grids),
        "poi_sample_grid_count": len(poi_counts),
        "poi_category_count": len(categories),
        "active_grid_count": int(
            activity_mask(scores["has_poi_activity"]).sum()
        ),
        "profile_count": len(specs),
    }


def _validated_numeric_columns(
    frame: pd.DataFrame,
    columns: list[str],
    path: str | Path,
) -> pd.DataFrame:
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    invalid = numeric.isna() & frame[columns].notna()
    if invalid.any().any():
        field = invalid.any(axis=0).loc[lambda value: value].index[0]
        raise ValueError(f"{path} 的 {field} 包含非数字值")
    numeric = numeric.fillna(0)
    if (numeric < 0).any().any():
        field = (numeric < 0).any(axis=0).loc[lambda value: value].index[0]
        raise ValueError(f"{path} 的 {field} 包含负数")
    return numeric


def build_poi_theme_summary_data(
    path: str | Path = POI_COUNTS_PATH,
) -> pd.DataFrame:
    """Aggregate the exact 15 configured POI fields into five themes."""
    categories = get_poi_categories()
    grouped_categories = [
        category
        for theme in POI_THEME_GROUPS.values()
        for category in theme["categories"]
    ]
    if (
        len(grouped_categories) != len(set(grouped_categories))
        or set(grouped_categories) != set(categories)
    ):
        raise ValueError("首页 POI 主题必须按配置中的 15 个类别精确分组")
    count_fields = [f"{category}_count" for category in grouped_categories]
    frame = load_required_csv(path, ["district_name", *count_fields])
    numeric = _validated_numeric_columns(frame, count_fields, path)
    district_counts = pd.concat(
        [frame[["district_name"]].astype(str), numeric],
        axis=1,
    ).groupby("district_name", as_index=False, sort=True)[count_fields].sum()
    rows: list[dict[str, Any]] = []
    for _, district in district_counts.iterrows():
        for theme_id, theme in POI_THEME_GROUPS.items():
            rows.append(
                {
                    "district_name": district["district_name"],
                    "poi_theme": theme_id,
                    "theme_label": theme["label"],
                    "poi_count": sum(
                        float(district[f"{category}_count"])
                        for category in theme["categories"]
                    ),
                    "category_labels": " / ".join(
                        categories[category]
                        for category in theme["categories"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_score_distribution_data(
    path: str | Path = SCORES_PATH,
) -> pd.DataFrame:
    """Return default-profile scores for active grids only."""
    score_fields = ["convenience_score", "light_food_score"]
    frame = load_required_csv(
        path,
        ["district_name", "has_poi_activity", *score_fields],
    )
    frame = frame.loc[activity_mask(frame["has_poi_activity"])].copy()
    frame[score_fields] = _validated_numeric_columns(
        frame,
        score_fields,
        path,
    )
    long_frame = frame.melt(
        id_vars="district_name",
        value_vars=score_fields,
        var_name="profile_id",
        value_name="score",
    )
    long_frame["profile_name"] = long_frame["profile_id"].map(
        {
            "convenience_score": "社区便利店",
            "light_food_score": "轻餐饮",
        }
    )
    return long_frame[
        ["district_name", "profile_id", "profile_name", "score"]
    ]


def build_score_average_data(
    path: str | Path = SCORES_PATH,
) -> pd.DataFrame:
    """Average the two default scores by district for the homepage."""
    distribution = build_score_distribution_data(path)
    return (
        distribution.groupby(
            ["district_name", "profile_id", "profile_name"],
            as_index=False,
            sort=True,
        )
        .agg(
            average_score=("score", "mean"),
            active_grid_count=("score", "size"),
        )
    )


def _poi_theme_chart(frame: pd.DataFrame) -> alt.Chart:
    theme_order = [
        theme["label"] for theme in POI_THEME_GROUPS.values()
    ]
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=2)
        .encode(
            x=alt.X(
                "poi_count:Q",
                title="原始 POI 数量",
                stack=None,
            ),
            y=alt.Y(
                "theme_label:N",
                title=None,
                sort=theme_order,
            ),
            yOffset=alt.YOffset("district_name:N"),
            color=alt.Color(
                "district_name:N",
                title="区县",
                scale=alt.Scale(
                    domain=["云岩区", "南明区", "观山湖区"],
                    range=["#176B4A", "#2F6FBE", "#D98252"],
                ),
            ),
            tooltip=[
                alt.Tooltip("theme_label:N", title="主题"),
                alt.Tooltip("category_labels:N", title="组成类别"),
                alt.Tooltip("district_name:N", title="区县"),
                alt.Tooltip("poi_count:Q", title="原始数量", format=",.0f"),
            ],
        )
        .properties(height=270)
    )


def _score_average_chart(frame: pd.DataFrame) -> alt.LayerChart:
    scale = alt.Scale(domain=[20, 40], clamp=True)
    score_axis = alt.Axis(values=[20, 25, 30, 35, 40])
    base = alt.Chart(frame)
    connector = base.mark_rule(
        color="#AAB2BF",
        strokeWidth=2,
    ).encode(
        x=alt.X(
            "min(average_score):Q",
            title="区县活跃网格平均得分",
            scale=scale,
            axis=score_axis,
        ),
        x2=alt.X2("max(average_score):Q"),
        y=alt.Y("district_name:N", title=None),
    )
    points = base.mark_point(filled=True, size=105).encode(
        x=alt.X("average_score:Q", scale=scale),
        y=alt.Y("district_name:N", title=None),
        color=alt.Color(
            "profile_name:N",
            title="评分方案",
            scale=alt.Scale(
                domain=["社区便利店", "轻餐饮"],
                range=["#176B4A", "#D98252"],
            ),
        ),
        tooltip=[
            alt.Tooltip("district_name:N", title="区县"),
            alt.Tooltip("profile_name:N", title="评分方案"),
            alt.Tooltip(
                "average_score:Q",
                title="平均得分",
                format=".2f",
            ),
            alt.Tooltip(
                "active_grid_count:Q",
                title="活跃网格数",
                format=".0f",
            ),
        ],
    )
    convenience_labels = (
        base.transform_filter(alt.datum.profile_name == "社区便利店")
        .mark_text(align="right", dx=-8, color="#176B4A", fontSize=11)
        .encode(
            x=alt.X("average_score:Q", scale=scale),
            y=alt.Y("district_name:N", title=None),
            text=alt.Text("average_score:Q", format=".1f"),
        )
    )
    food_labels = (
        base.transform_filter(alt.datum.profile_name == "轻餐饮")
        .mark_text(align="left", dx=8, color="#D98252", fontSize=11)
        .encode(
            x=alt.X("average_score:Q", scale=scale),
            y=alt.Y("district_name:N", title=None),
            text=alt.Text("average_score:Q", format=".1f"),
        )
    )
    return (
        connector + points + convenience_labels + food_labels
    ).properties(height=210)


def render(st_module: Any | None = None) -> None:
    """Render the project overview."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "项目总览",
        "贵阳市典型区县社区商业智能选址工作台",
    )
    st.markdown(
        "系统以区县作为背景约束，以 1km 评价网格作为评分对象，"
        "用于便利店、轻餐饮及有效自定义方案的前期调研排序。"
    )
    try:
        metrics = load_overview_metrics()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    render_metric_cards(
        st,
        [
            ("目标区县", metrics["district_count"], "贵阳市首版研究范围"),
            (
                "空间评价网格",
                metrics["spatial_grid_count"],
                "三区完整空间底板",
            ),
            (
                "POI 类别",
                metrics["poi_category_count"],
                "统一关键词采集口径",
            ),
            (
                "活跃推荐网格",
                metrics["active_grid_count"],
                "具备 POI 活动和有效排名",
            ),
        ],
    )
    st.caption(
        f"当前已采集 {metrics['poi_sample_grid_count']} 个样本网格，"
        f"可用评分方案 {metrics['profile_count']} 套。"
    )
    try:
        theme_data = build_poi_theme_summary_data()
        average_data = build_score_average_data()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return

    st.subheader("数据概览")
    heatmap_column, score_column = st.columns([1.35, 1], gap="large")
    with heatmap_column:
        st.markdown("**三区五类 POI 主题摘要**")
        st.altair_chart(_poi_theme_chart(theme_data), width="stretch")
        st.caption(
            "15 类 POI 汇总为社区零售、餐饮消费、生活客群、"
            "商业办公和交通配套；细分类别在区域对比页查看。"
        )
    with score_column:
        st.markdown("**活跃网格区县平均得分**")
        st.altair_chart(_score_average_chart(average_data), width="stretch")
        st.caption(
            "每个区县按活跃网格计算两类默认方案平均分；"
            "完整网格排名和分解在网格推荐页查看。"
        )
    st.info(
        "当前结果是关键词 POI 样本统一口径下的相对评价，"
        "不替代租金、客流、经营数据和现场尽调。"
    )
