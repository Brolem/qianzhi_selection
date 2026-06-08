"""Streamlit entry point for Qianzhi Selection.

Run after installing dependencies:
    streamlit run src/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from .config import get_path
except ImportError:
    from config import get_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGION_STAGE_RESULT = get_path("results_region_stage") / "region_stage_score_result.csv"
GRID_STAGE_RESULT = get_path("results_grid_stage") / "grid_stage_score_result.csv"
SELECTED_REGIONS = get_path("results_region_stage") / "selected_regions_for_grid_stage.csv"


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit("Please install streamlit before running the app.") from exc

    st.set_page_config(page_title="黔址优选", layout="wide")
    st.title("黔址优选：社区商业智能选址决策系统")
    if not REGION_STAGE_RESULT.exists() or not GRID_STAGE_RESULT.exists():
        st.warning("尚未生成两阶段推荐结果，请先运行：python src/two_stage_site_selection.py --top-n 5")
        return

    st.markdown(
        """
        当前项目边界：
        - 业务对象：社区便利店、轻餐饮
        - 第一阶段：OSM 边界评价区域粗筛
        - 第二阶段：入选区域内 1km 评价网格细筛
        - 推荐结果：网格级优先考察区域，不是门牌号级推荐
        """
    )

    business_type = st.radio("业态", ["社区便利店", "轻餐饮"], horizontal=True)
    if business_type == "社区便利店":
        score_col = "convenience_score"
        rank_col = "rank_convenience"
    else:
        score_col = "light_catering_score"
        rank_col = "rank_light_catering"

    region_df = pd.read_csv(REGION_STAGE_RESULT)
    grid_df = pd.read_csv(GRID_STAGE_RESULT)

    if SELECTED_REGIONS.exists():
        selected_df = pd.read_csv(SELECTED_REGIONS)
        st.subheader("进入 1km 细筛的区域")
        st.dataframe(
            selected_df[
                [
                    "selection_rank",
                    "region_id",
                    "region_name",
                    "rank_convenience",
                    "rank_light_catering",
                    "main_advantage",
                    "main_risk",
                ]
            ],
            use_container_width=True,
        )

    st.subheader("第一阶段：区域推荐榜")
    region_display_cols = ["region_id", "region_name", score_col, rank_col, "main_advantage", "main_risk"]
    st.dataframe(region_df.sort_values(rank_col)[region_display_cols].head(30), use_container_width=True)

    st.subheader("第二阶段：1km 评价网格推荐榜")
    if "grid_region_name" in grid_df.columns:
        region_names = sorted(grid_df["grid_region_name"].dropna().astype(str).unique())
        selected_name = st.selectbox("筛选入选区域", ["全部"] + region_names)
        if selected_name != "全部":
            grid_df = grid_df[grid_df["grid_region_name"].astype(str).eq(selected_name)]

    grid_display_cols = [
        "region_id",
        "grid_region_name",
        "grid_center_lon",
        "grid_center_lat",
        score_col,
        rank_col,
        "main_advantage",
        "main_risk",
    ]
    st.dataframe(grid_df.sort_values(rank_col)[grid_display_cols].head(50), use_container_width=True)


if __name__ == "__main__":
    main()
