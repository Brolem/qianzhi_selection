"""Project overview page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
from src.profile_catalog import ResultProfileSpec


def load_overview_metrics(
    *,
    districts_path: str | Path = TARGET_DISTRICTS_PATH,
    grids_path: str | Path = SPATIAL_GRIDS_PATH,
    poi_counts_path: str | Path = POI_COUNTS_PATH,
    scores_path: str | Path = SCORES_PATH,
    profile_specs: dict[str, ResultProfileSpec] | None = None,
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
    return {
        "district_count": len(districts),
        "spatial_grid_count": len(grids),
        "poi_sample_grid_count": len(poi_counts),
        "active_grid_count": int(
            activity_mask(scores["has_poi_activity"]).sum()
        ),
        "profile_count": len(specs),
    }


def render(st_module: Any | None = None) -> None:
    """Render the project overview."""
    st = get_streamlit(st_module)
    st.title("黔址优选")
    st.caption("贵阳市典型区县社区商业智能选址工作台")
    st.markdown(
        "系统以区县作为背景约束，以 1km 评价网格作为评分对象，"
        "用于便利店、轻餐饮及有效自定义方案的前期调研排序。"
    )
    try:
        metrics = load_overview_metrics()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(str(exc))
        return
    columns = st.columns(5)
    labels = [
        ("目标区县", "district_count"),
        ("空间网格", "spatial_grid_count"),
        ("POI 样本网格", "poi_sample_grid_count"),
        ("活跃评分网格", "active_grid_count"),
        ("评分方案", "profile_count"),
    ]
    for column, (label, key) in zip(columns, labels):
        column.metric(label, metrics[key])
    st.info(
        "当前结果是关键词 POI 样本统一口径下的相对评价，"
        "不替代租金、客流、经营数据和现场尽调。"
    )
