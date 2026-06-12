"""Project boundaries and implemented-capability notes."""

from __future__ import annotations

from typing import Any

from src.pages.common import get_streamlit


def render(st_module: Any | None = None) -> None:
    """Render current v2 scope and limitations."""
    st = get_streamlit(st_module)
    st.header("项目说明")
    st.markdown(
        """
        **当前已实施**

        - 高德区县边界、统一 1km 空间网格和 60 个网格的 POI 样本采集。
        - 六维指标工程、便利店与轻餐饮默认评分、自定义六维权重方案。
        - 790 个空间网格地图、41 个活跃网格排名和 DeepSeek 智能报告。

        **数据边界**

        - 官方宏观与就业数据当前为贵州省级，只作市场背景和适用范围说明。
        - POI 统计采用统一关键词查询口径，适合相对比较，不代表完整设施总量。
        - 19 个无 POI 活动的样本网格保留审计状态，不进入推荐排名。

        **使用边界**

        - 结果用于前期调研排序和经营研判。
        - 不提供真实租金、客流、营收或盈利预测。
        - 不输出门牌号级推荐，实地决策仍需现场复核。
        """
    )
