"""Report generation module for intelligent site selection reports."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from .config import ensure_output_dirs, get_path
except ImportError:
    from config import ensure_output_dirs, get_path


GRID_STAGE_RESULT = get_path("results_grid_stage") / "grid_stage_score_result.csv"
REPORTS_DIR = get_path("reports")


def build_report_prompt(region_record: Mapping[str, Any], business_type: str) -> str:
    """Build a prompt for LLM-based site selection report generation."""
    return f"""
请根据以下结构化指标，生成一份社区商业智能选址报告。

业态：{business_type}
区域信息：{dict(region_record)}

请按以下结构输出：
1. 区域基本画像
2. 消费潜力分析
3. 就业客群分析
4. 交通与配套分析
5. 竞争态势分析
6. 推荐理由
7. 风险提示
8. 开店建议

要求：所有结论必须基于输入指标，不要编造真实地名、真实门店和真实经营数据。
""".strip()


def _format_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return str(value)


def generate_template_report(region_record: Mapping[str, Any], business_type: str) -> str:
    """Generate a deterministic template report before an LLM API is connected."""
    region_name = region_record.get("grid_region_name", region_record.get("region_name", "评价区域"))
    grid_id = region_record.get("region_id", "评价网格")
    score_field = "convenience_score" if business_type == "社区便利店" else "light_catering_score"
    score = _format_score(region_record.get(score_field, "待计算"))
    advantage = region_record.get("main_advantage", "暂无")
    risk = region_record.get("main_risk", "暂无")
    lon = region_record.get("grid_center_lon", "")
    lat = region_record.get("grid_center_lat", "")
    return f"""# {region_name} {business_type}选址报告

## 一、综合判断

评价网格 `{grid_id}` 的综合评分为 {score}。本报告由已接入的数据和评分结果生成，结论仅作为选址辅助参考。

## 二、空间位置

- 所属区域：{region_name}
- 网格中心经度：{lon}
- 网格中心纬度：{lat}

## 三、推荐理由

系统基于交通可达性、消费潜力、共生业态、竞争压力和区域发展基础生成推荐理由。当前主要优势为：{advantage}。

## 四、风险提示

当前主要风险为：{risk}。真实开店决策仍需结合租金、现场客流、门店面积、竞品实地情况和经营策略复核。

## 五、数据来源与限制

官方宏观经济和就业数据用于贵州整体市场背景说明；OSM 空间数据用于区域和网格差异计算。当前未接入真实租金、实时客流、停车条件和工商信用数据。
"""


def load_grid_results(path: str | Path = GRID_STAGE_RESULT) -> pd.DataFrame:
    """Load grid-stage score results."""
    result_path = Path(path)
    if not result_path.exists():
        raise FileNotFoundError(f"网格细筛结果不存在：{result_path}")
    return pd.read_csv(result_path)


def generate_site_report(grid_id: str, business_type: str, result_path: str | Path = GRID_STAGE_RESULT) -> str:
    """Generate a site-selection report for one evaluation grid."""
    data = load_grid_results(result_path)
    if "region_id" not in data.columns:
        raise KeyError("网格细筛结果缺少 region_id 字段")
    matched = data[data["region_id"].astype(str).eq(str(grid_id))]
    if matched.empty:
        raise KeyError(f"未找到评价网格：{grid_id}")
    return generate_template_report(matched.iloc[0].to_dict(), business_type)


def export_report(grid_id: str, business_type: str, output_path: str | Path | None = None) -> Path:
    """Export a Markdown report for one evaluation grid."""
    ensure_output_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path is not None else REPORTS_DIR / f"{grid_id}_{business_type}_选址报告.md"
    path.write_text(generate_site_report(grid_id, business_type), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="生成评价网格选址报告。")
    parser.add_argument("--grid-id", default=None, help="评价网格 region_id；不提供时默认使用评分结果第一行。")
    parser.add_argument("--business-type", default="社区便利店", choices=["社区便利店", "轻餐饮"])
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    grid_id = args.grid_id
    if grid_id is None:
        data = load_grid_results()
        if data.empty:
            raise ValueError("网格细筛结果为空，无法生成报告。")
        grid_id = str(data.iloc[0]["region_id"])
    output_path = export_report(grid_id, args.business_type)
    print(output_path)


if __name__ == "__main__":
    main()
