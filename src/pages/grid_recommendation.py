"""Grid recommendation, interactive weighting and custom-profile saving."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import altair as alt
import pandas as pd

from src.interactive_scoring import (
    EQUAL_PERCENTAGES,
    WEIGHT_LABELS,
    normalize_percentages,
    percentage_total,
    profile_from_percentages,
    save_custom_profile,
    score_custom_preview,
    weight_preset_percentages,
)
from src.pages.common import (
    RESULTS_DIR,
    SCORING_INPUT_PATH,
    activity_mask,
    get_streamlit,
    load_profile_options,
    load_required_csv,
)
from src.profile_catalog import ResultProfileSpec, TEMPLATE_FIELDS
from src.scoring_model import WEIGHT_FIELDS, ScoringProfile
from src.ui.workbench import render_page_header


NEW_CUSTOM_PROFILE = "新建自定义方案"
TEMPLATE_LABELS = {
    "社区零售型": "community_retail",
    "餐饮服务型": "food_service",
}
WEIGHT_STATE_KEYS = {
    field: f"grid_weight_{field}" for field in WEIGHT_FIELDS
}
SCORING_INPUT_FIELDS = [
    "grid_id",
    "district_name",
    "poi_total_count",
    "has_poi_activity",
    "traffic_accessibility",
    "consumption_potential",
    "employment_customer_proxy",
    "business_atmosphere",
    "convenience_synergy_score",
    "light_food_synergy_score",
    "convenience_competition_pressure",
    "light_food_competition_pressure",
]


@dataclass(frozen=True)
class RecommendationView:
    """One result table and its exact display fields."""

    profile_id: str
    profile_name: str
    template_id: str
    weights: dict[str, float]
    frame: pd.DataFrame
    score_field: str
    rank_field: str
    district_rank_field: str
    synergy_field: str
    competition_score_field: str
    advantage_field: str
    risk_field: str
    level_field: str


def load_scoring_input(path=SCORING_INPUT_PATH) -> pd.DataFrame:
    """Load the exact Step 7 scoring input used for interactive previews."""
    return load_required_csv(path, SCORING_INPUT_FIELDS)


def ranked_recommendation_rows(
    frame: pd.DataFrame,
    *,
    rank_field: str,
    district_rank_field: str,
    district_name: str,
    limit: int,
) -> pd.DataFrame:
    """Return active rows ordered by global or district rank."""
    required = [
        "grid_id",
        "district_name",
        "has_poi_activity",
        rank_field,
        district_rank_field,
    ]
    missing = [field for field in required if field not in frame.columns]
    if missing:
        raise KeyError("评分结果缺少字段：" + ", ".join(missing))
    result = frame.loc[activity_mask(frame["has_poi_activity"])].copy()
    selected_rank = rank_field
    if district_name != "全部":
        result = result.loc[
            result["district_name"].astype(str).eq(district_name)
        ]
        selected_rank = district_rank_field
    result[selected_rank] = pd.to_numeric(
        result[selected_rank],
        errors="coerce",
    )
    result = result.loc[result[selected_rank].notna()].copy()
    result["grid_id"] = result["grid_id"].astype(str)
    return (
        result.sort_values(
            [selected_rank, "grid_id"],
            ascending=[True, True],
            kind="mergesort",
        )
        .head(limit)
        .reset_index(drop=True)
    )


def metric_breakdown_data(
    row: pd.Series,
    *,
    synergy_field: str,
    competition_score_field: str,
) -> pd.DataFrame:
    """Build the six positive-direction dimensions for one grid."""
    fields = [
        ("交通可达性", "traffic_accessibility"),
        ("消费潜力", "consumption_potential"),
        ("就业客群代理", "employment_customer_proxy"),
        ("共生业态", synergy_field),
        ("低竞争得分", competition_score_field),
        ("商业氛围", "business_atmosphere"),
    ]
    missing = [field for _, field in fields if field not in row.index]
    if missing:
        raise KeyError("评分结果缺少字段：" + ", ".join(missing))
    values = pd.to_numeric(
        pd.Series({label: row[field] for label, field in fields}),
        errors="coerce",
    )
    if values.isna().any():
        field = values.loc[values.isna()].index[0]
        raise ValueError(f"{field}包含非数字值")
    return pd.DataFrame(
        {
            "metric_name": values.index,
            "metric_value": values.values,
        }
    )


def _view_from_result_profile(profile: ResultProfileSpec) -> RecommendationView:
    required = [
        "grid_id",
        "district_name",
        "has_poi_activity",
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        profile.score_field,
        profile.rank_field,
        profile.district_rank_field,
        profile.synergy_field,
        profile.competition_score_field,
        profile.advantage_field,
        profile.risk_field,
        profile.level_field,
    ]
    frame = load_required_csv(profile.result_path, required)
    return RecommendationView(
        profile_id=profile.profile_id,
        profile_name=profile.profile_name,
        template_id=profile.template_id,
        weights=profile.weights,
        frame=frame,
        score_field=profile.score_field,
        rank_field=profile.rank_field,
        district_rank_field=profile.district_rank_field,
        synergy_field=profile.synergy_field,
        competition_score_field=profile.competition_score_field,
        advantage_field=profile.advantage_field,
        risk_field=profile.risk_field,
        level_field=profile.level_field,
    )


def _view_from_preview(
    profile: ScoringProfile,
    frame: pd.DataFrame,
) -> RecommendationView:
    template_fields = TEMPLATE_FIELDS[profile.template_id]
    return RecommendationView(
        profile_id=profile.profile_id,
        profile_name=profile.profile_name,
        template_id=profile.template_id,
        weights=profile.weights,
        frame=frame,
        score_field="profile_score",
        rank_field="profile_rank",
        district_rank_field="district_profile_rank",
        synergy_field=template_fields["synergy_field"],
        competition_score_field="profile_competition_score",
        advantage_field="profile_main_advantage",
        risk_field="profile_main_risk",
        level_field="profile_recommendation_level",
    )


def _set_weight_state(st: Any, percentages: dict[str, float]) -> None:
    for field in WEIGHT_FIELDS:
        st.session_state[WEIGHT_STATE_KEYS[field]] = float(percentages[field])


def _initialize_weight_state(st: Any) -> None:
    defaults = weight_preset_percentages("convenience")
    for field in WEIGHT_FIELDS:
        key = WEIGHT_STATE_KEYS[field]
        if key not in st.session_state:
            st.session_state[key] = defaults[field]


def _current_percentages(st: Any) -> dict[str, float]:
    return {
        field: float(st.session_state[WEIGHT_STATE_KEYS[field]])
        for field in WEIGHT_FIELDS
    }


def _apply_preset(st: Any, percentages: dict[str, float]) -> None:
    _set_weight_state(st, percentages)
    st.rerun()


def _normalize_weight_state(st: Any) -> None:
    _set_weight_state(st, normalize_percentages(_current_percentages(st)))


def _weight_chart(percentages: dict[str, float]) -> alt.Chart:
    data = pd.DataFrame(
        {
            "metric_name": [WEIGHT_LABELS[field] for field in WEIGHT_FIELDS],
            "percentage": [percentages[field] for field in WEIGHT_FIELDS],
        }
    )
    return (
        alt.Chart(data)
        .mark_bar(color="#2F6FBE", cornerRadiusEnd=2)
        .encode(
            x=alt.X(
                "percentage:Q",
                title="实际送入评分模型的权重（%）",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y(
                "metric_name:N",
                title=None,
                sort=[WEIGHT_LABELS[field] for field in WEIGHT_FIELDS],
            ),
            tooltip=[
                alt.Tooltip("metric_name:N", title="指标"),
                alt.Tooltip("percentage:Q", title="权重", format=".2f"),
            ],
        )
        .properties(height=210)
    )


def _metric_chart(frame: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(frame)
        .mark_bar(color="#176B4A", cornerRadiusEnd=2)
        .encode(
            x=alt.X(
                "metric_value:Q",
                title="指标得分",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y(
                "metric_name:N",
                title=None,
                sort=frame["metric_name"].tolist(),
            ),
            tooltip=[
                alt.Tooltip("metric_name:N", title="指标"),
                alt.Tooltip("metric_value:Q", title="得分", format=".2f"),
            ],
        )
        .properties(height=240)
    )


def _render_custom_builder(
    st: Any,
    scoring_input: pd.DataFrame,
) -> RecommendationView | None:
    st.markdown("**指标模板与 100 分权重预算器**")
    template_label = st.selectbox(
        "指标模板",
        list(TEMPLATE_LABELS),
        key="grid_custom_template",
    )
    template_id = TEMPLATE_LABELS[template_label]
    _initialize_weight_state(st)

    preset_columns = st.columns(4, gap="small")
    presets = [
        ("便利店预设", weight_preset_percentages("convenience")),
        ("轻餐饮预设", weight_preset_percentages("light_food")),
        ("平均分配", EQUAL_PERCENTAGES),
        ("重置", {field: 0.0 for field in WEIGHT_FIELDS}),
    ]
    for column, (label, values) in zip(preset_columns, presets):
        with column:
            if st.button(label, use_container_width=True):
                _apply_preset(st, values)

    input_columns = st.columns(3, gap="medium")
    for index, field in enumerate(WEIGHT_FIELDS):
        with input_columns[index % 3]:
            st.number_input(
                f"{WEIGHT_LABELS[field]}（%）",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                format="%.2f",
                key=WEIGHT_STATE_KEYS[field],
            )

    percentages = _current_percentages(st)
    total = percentage_total(percentages)
    remaining = Decimal("100.00") - total
    status_columns = st.columns(3, gap="medium")
    status_columns[0].metric("已分配", f"{total:.2f}%")
    if remaining >= 0:
        status_columns[1].metric("剩余", f"{remaining:.2f}%")
    else:
        status_columns[1].metric("超出", f"{abs(remaining):.2f}%")
    status_columns[2].metric(
        "保存状态",
        "可保存" if total == Decimal("100.00") else "仅预览",
    )

    if total == 0:
        st.warning("六项权重全部为 0，无法计算即时评分。")
        return None

    normalized = normalize_percentages(percentages)
    if total != Decimal("100.00"):
        st.info(
            "输入合计不是 100.00%，即时预览将使用下方归一后权重；"
            "正式保存仍要求输入合计精确为 100.00%。"
        )
    st.button(
        "一键归一到 100.00%",
        on_click=_normalize_weight_state,
        args=(st,),
        use_container_width=True,
    )
    st.altair_chart(_weight_chart(normalized), width="stretch")
    st.caption(
        "实际送入后端："
        + "；".join(
            f"{WEIGHT_LABELS[field]} {normalized[field]:.2f}%"
            for field in WEIGHT_FIELDS
        )
    )

    preview_profile = profile_from_percentages(
        "preview_profile",
        f"即时预览｜{template_label}",
        template_id,
        percentages,
        normalize=True,
    )
    preview_frame = score_custom_preview(scoring_input, preview_profile)

    st.markdown("**保存为正式方案**")
    identity_columns = st.columns(2, gap="medium")
    with identity_columns[0]:
        profile_name = st.text_input(
            "中文方案名称",
            key="grid_custom_profile_name",
        )
    with identity_columns[1]:
        profile_id = st.text_input(
            "profile_id",
            help="仅允许小写字母、数字和下划线。",
            key="grid_custom_profile_id",
        )
    save_enabled = (
        total == Decimal("100.00")
        and bool(profile_name.strip())
        and bool(profile_id.strip())
    )
    if st.button(
        "保存评分方案",
        disabled=not save_enabled,
        type="primary",
        use_container_width=True,
    ):
        try:
            save_custom_profile(
                scoring_input,
                profile_id=profile_id.strip(),
                profile_name=profile_name.strip(),
                template_id=template_id,
                percentages=percentages,
                results_dir=RESULTS_DIR,
            )
        except (FileExistsError, KeyError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.session_state["grid_profile_saved_message"] = (
                f"评分方案已保存：{profile_name.strip()} ({profile_id.strip()})"
            )
            st.rerun()
    return _view_from_preview(preview_profile, preview_frame)


def _result_table(
    rows: pd.DataFrame,
    view: RecommendationView,
    *,
    district_name: str,
) -> pd.DataFrame:
    rank_field = (
        view.rank_field
        if district_name == "全部"
        else view.district_rank_field
    )
    columns = [
        "grid_id",
        "district_name",
        view.score_field,
        rank_field,
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        view.synergy_field,
        view.competition_score_field,
        "business_atmosphere",
        view.advantage_field,
        view.risk_field,
        view.level_field,
    ]
    missing = [field for field in columns if field not in rows.columns]
    if missing:
        raise KeyError("评分结果缺少字段：" + ", ".join(missing))
    return rows[columns].rename(
        columns={
            "grid_id": "网格标识",
            "district_name": "区县",
            view.score_field: "综合得分",
            rank_field: "排名",
            "traffic_accessibility": "交通可达性",
            "consumption_potential": "消费潜力",
            "employment_customer_proxy": "就业客群代理",
            view.synergy_field: "共生业态",
            view.competition_score_field: "低竞争得分",
            "business_atmosphere": "商业氛围",
            view.advantage_field: "主要优势",
            view.risk_field: "主要风险",
            view.level_field: "推荐等级",
        }
    )


def _render_results(st: Any, view: RecommendationView) -> None:
    active = view.frame.loc[
        activity_mask(view.frame["has_poi_activity"])
    ].copy()
    districts = sorted(
        active["district_name"].dropna().astype(str).unique().tolist()
    )
    district_name = st.selectbox(
        "推荐范围",
        ["全部", *districts],
        key="grid_recommendation_district",
    )
    limit = 10 if district_name == "全部" else 5
    rows = ranked_recommendation_rows(
        view.frame,
        rank_field=view.rank_field,
        district_rank_field=view.district_rank_field,
        district_name=district_name,
        limit=limit,
    )
    heading = "全局 Top 10" if district_name == "全部" else f"{district_name} Top 5"
    st.subheader(heading)
    st.dataframe(
        _result_table(rows, view, district_name=district_name),
        width="stretch",
        hide_index=True,
    )

    all_ranked = ranked_recommendation_rows(
        view.frame,
        rank_field=view.rank_field,
        district_rank_field=view.district_rank_field,
        district_name="全部",
        limit=len(view.frame),
    )
    if all_ranked.empty:
        st.warning("当前评分方案没有可展示的活跃网格。")
        return
    labels = {
        str(row["grid_id"]): (
            f"{row['district_name']}｜全局第 {int(row[view.rank_field])} 名｜"
            f"{float(row[view.score_field]):.2f} 分"
        )
        for _, row in all_ranked.iterrows()
    }
    selected_grid = st.selectbox(
        "查看网格六维分解",
        list(labels),
        format_func=labels.get,
        key=f"grid_breakdown_{view.profile_id}",
    )
    selected = all_ranked.loc[
        all_ranked["grid_id"].astype(str).eq(selected_grid)
    ].iloc[0]
    detail_columns = st.columns(3, gap="medium")
    detail_columns[0].metric(
        "综合得分",
        f"{float(selected[view.score_field]):.2f}",
    )
    detail_columns[1].metric(
        "全局排名",
        f"{int(selected[view.rank_field])}",
    )
    detail_columns[2].metric(
        "推荐等级",
        str(selected[view.level_field]),
    )
    breakdown = metric_breakdown_data(
        selected,
        synergy_field=view.synergy_field,
        competition_score_field=view.competition_score_field,
    )
    st.altair_chart(_metric_chart(breakdown), width="stretch")
    explanation_columns = st.columns(2, gap="large")
    explanation_columns[0].info(
        f"主要优势：{selected[view.advantage_field]}"
    )
    explanation_columns[1].warning(
        f"主要风险：{selected[view.risk_field]}"
    )


def render(st_module: Any | None = None) -> None:
    """Render the unified Step 15 decision page."""
    st = get_streamlit(st_module)
    render_page_header(
        st,
        "网格推荐",
        "统一完成方案选择、自定义权重、即时评分、推荐排序和指标分解。",
    )
    saved_message = st.session_state.pop("grid_profile_saved_message", None)
    if saved_message:
        st.success(saved_message)

    try:
        scoring_input = load_scoring_input()
        profiles = load_profile_options()
        with st.container(border=True):
            st.subheader("评分参数")
            selected_source = st.selectbox(
                "方案来源",
                [*profiles, NEW_CUSTOM_PROFILE],
                key="grid_recommendation_source",
            )
            if selected_source == NEW_CUSTOM_PROFILE:
                view = _render_custom_builder(st, scoring_input)
            else:
                view = _view_from_result_profile(profiles[selected_source])
                template_name = next(
                    label
                    for label, template_id in TEMPLATE_LABELS.items()
                    if template_id == view.template_id
                )
                st.caption(
                    f"当前方案：{view.profile_name}；指标模板：{template_name}。"
                )
        if view is not None:
            _render_results(st, view)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
