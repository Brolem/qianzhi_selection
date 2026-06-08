"""Report generation module for intelligent site selection reports."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from ..config import ensure_output_dirs, get_path
except ImportError:
    from src.config import ensure_output_dirs, get_path


GRID_STAGE_RESULT = get_path("results_grid_stage") / "grid_stage_score_result.csv"
REPORTS_DIR = get_path("reports")
DEFAULT_QIANWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QIANWEN_MODEL = "qwen3.7-plus"


class MissingQianwenConfigError(RuntimeError):
    """Raised when Qianwen report generation lacks required configuration."""


def _format_score(value: Any) -> str:
    """Format numeric values consistently in reports."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return str(value)
    return f"{float(numeric):.3f}"


def _score_field_for_business(business_type: str) -> str:
    """Return the exact score field for a supported business type."""
    if business_type == "社区便利店":
        return "convenience_score"
    if business_type == "轻餐饮":
        return "light_catering_score"
    raise ValueError(f"不支持的业态：{business_type}")


def _record_value(record: Mapping[str, Any], key: str, default: str = "当前未接入，后续可补充") -> Any:
    """Read a value from the scoring record with a visible missing-data notice."""
    value = record.get(key, default)
    if pd.isna(value):
        return default
    return value


def _grid_identifier(record: Mapping[str, Any]) -> str:
    """Return the exact grid identifier used in scoring outputs."""
    return str(record.get("grid_id", record.get("region_id", "评价网格")))


def _report_payload(record: Mapping[str, Any], business_type: str) -> dict[str, Any]:
    """Build the structured payload sent to the report generator."""
    score_field = _score_field_for_business(business_type)
    keys = [
        "region_id",
        "grid_id",
        "grid_region_name",
        "parent_region_id",
        "centroid_lon",
        "centroid_lat",
        "area_km2",
        "traffic_accessibility",
        "consumption_potential",
        "synergy_score",
        "competition_pressure",
        "development_basis",
        "convenience_score",
        "light_catering_score",
        "main_advantage",
        "main_risk",
    ]
    payload = {key: _record_value(record, key) for key in keys if key in record}
    payload["business_type"] = business_type
    payload["score_field"] = score_field
    payload["business_score"] = _record_value(record, score_field)
    payload["missing_data_notice"] = "真实租金、真实客流、真实营收、停车条件、工商信用当前未接入，后续可补充。"
    return payload


def build_report_prompt(region_record: Mapping[str, Any], business_type: str) -> str:
    """Build a strict Qianwen prompt from structured scoring fields."""
    payload = _report_payload(region_record, business_type)
    return f"""
请根据下方结构化选址评分结果，生成一份 Markdown 格式的社区商业智能选址报告。

结构化输入：
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}

必须按以下十个二级标题输出，标题文字必须完全保留：
## 一、候选网格基本信息
## 二、适配业态判断
## 三、交通可达性分析
## 四、消费潜力分析
## 五、共生业态分析
## 六、竞争压力分析
## 七、主要优势
## 八、主要风险
## 九、经营建议
## 十、数据来源与限制说明

要求：
1. 所有结论必须来自结构化输入字段。
2. 不允许编造真实租金、真实客流、真实营收。
3. 对真实租金、真实客流、真实营收、停车条件、工商信用等缺失数据，必须写“当前未接入，后续可补充”。
4. 当前结果是区域粗筛和 1km 评价网格细筛，不输出具体门牌号。
5. 语言正式、适合初赛方案或演示系统展示。
""".strip()


def create_qianwen_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Any:
    """Create an OpenAI-compatible Qianwen client from environment configuration."""
    resolved_api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
    if not resolved_api_key:
        raise MissingQianwenConfigError("缺少 DASHSCOPE_API_KEY，无法调用千问/DashScope 生成报告。")
    resolved_base_url = base_url or os.getenv("QIANWEN_BASE_URL", DEFAULT_QIANWEN_BASE_URL)
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise MissingQianwenConfigError("缺少 openai 依赖，请先安装 requirements.txt。") from exc
    return OpenAI(api_key=resolved_api_key, base_url=resolved_base_url)


def call_qianwen_report(
    region_record: Mapping[str, Any],
    business_type: str,
    *,
    llm_client: Any | None = None,
    model: str | None = None,
) -> str:
    """Generate a report through Qianwen OpenAI-compatible Chat Completions."""
    client = llm_client or create_qianwen_client()
    resolved_model = model or os.getenv("QIANWEN_MODEL", DEFAULT_QIANWEN_MODEL)
    completion = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {
                "role": "system",
                "content": "你是商业选址分析师，只能依据输入字段生成报告，不得编造缺失数据。",
            },
            {"role": "user", "content": build_report_prompt(region_record, business_type)},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content


def generate_template_report(region_record: Mapping[str, Any], business_type: str) -> str:
    """Generate a deterministic ten-section template report."""
    region_name = str(region_record.get("grid_region_name", region_record.get("region_name", "评价区域")))
    grid_id = _grid_identifier(region_record)
    score_field = _score_field_for_business(business_type)
    score = _format_score(region_record.get(score_field, "待计算"))
    advantage = _record_value(region_record, "main_advantage", "当前未接入，后续可补充")
    risk = _record_value(region_record, "main_risk", "当前未接入，后续可补充")
    lon = _record_value(region_record, "centroid_lon", _record_value(region_record, "grid_center_lon"))
    lat = _record_value(region_record, "centroid_lat", _record_value(region_record, "grid_center_lat"))
    area = _format_score(_record_value(region_record, "area_km2", _record_value(region_record, "grid_area_sq_km")))
    traffic = _format_score(_record_value(region_record, "traffic_accessibility"))
    consumption = _format_score(_record_value(region_record, "consumption_potential"))
    synergy = _format_score(_record_value(region_record, "synergy_score"))
    competition = _format_score(_record_value(region_record, "competition_pressure"))

    return f"""# {region_name} {business_type}选址报告

本报告为模板生成，用于 API 不可用或离线验证场景；大模型生成时会基于同一组结构化字段输出。

## 一、候选网格基本信息

- grid_id：`{grid_id}`
- 所属区域：{region_name}
- 网格中心经度：{lon}
- 网格中心纬度：{lat}
- 面积：{area} 平方公里

## 二、适配业态判断

当前业态为{business_type}，对应评分字段为 `{score_field}`，综合评分为 {score}。该判断仅基于已接入的空间评分字段。

## 三、交通可达性分析

交通可达性得分为 {traffic}，主要来自道路密度、路口密度和公交站密度等字段。

## 四、消费潜力分析

消费潜力得分为 {consumption}，主要来自居住、商业、零售用地和商超配套等字段。

## 五、共生业态分析

共生业态得分为 {synergy}，主要来自学校、医院、商场、办公和居住配套等字段。

## 六、竞争压力分析

竞争压力得分为 {competition}。竞争压力是风险分析字段，不代表真实客流或真实营收。

## 七、主要优势

当前主要优势为：{advantage}。

## 八、主要风险

当前主要风险为：{risk}。

## 九、经营建议

建议将该网格作为前期实地调研对象，结合现场客流、租金水平、门店面积、竞品分布和停车条件进一步复核。

## 十、数据来源与限制说明

官方宏观经济和就业数据用于贵州整体市场背景说明；OSM 空间数据用于区域和 1km 评价网格差异计算。真实租金、真实客流、真实营收、停车条件、工商信用当前未接入，后续可补充。
"""


def load_grid_results(path: str | Path = GRID_STAGE_RESULT) -> pd.DataFrame:
    """Load grid-stage score results."""
    result_path = Path(path)
    if not result_path.exists():
        raise FileNotFoundError(f"网格细筛结果不存在：{result_path}")
    return pd.read_csv(result_path)


def _find_grid_record(data: pd.DataFrame, grid_id: str) -> dict[str, Any]:
    """Find one grid record by exact grid identifier fields."""
    if "region_id" not in data.columns:
        raise KeyError("网格细筛结果缺少 region_id 字段")
    region_match = data["region_id"].astype(str).eq(str(grid_id))
    if "grid_id" in data.columns:
        grid_match = data["grid_id"].astype(str).eq(str(grid_id))
        matched = data[region_match | grid_match]
    else:
        matched = data[region_match]
    if matched.empty:
        raise KeyError(f"未找到评价网格：{grid_id}")
    return matched.iloc[0].to_dict()


def generate_site_report(
    grid_id: str,
    business_type: str,
    result_path: str | Path = GRID_STAGE_RESULT,
    *,
    use_llm: bool = True,
    llm_client: Any | None = None,
    model: str | None = None,
) -> str:
    """Generate a site-selection report for one evaluation grid."""
    data = load_grid_results(result_path)
    record = _find_grid_record(data, grid_id)
    if use_llm:
        return call_qianwen_report(record, business_type, llm_client=llm_client, model=model)
    return generate_template_report(record, business_type)


def export_report(
    grid_id: str,
    business_type: str,
    output_path: str | Path | None = None,
    *,
    result_path: str | Path = GRID_STAGE_RESULT,
    use_llm: bool = True,
    llm_client: Any | None = None,
    model: str | None = None,
) -> Path:
    """Export a Markdown report for one evaluation grid."""
    ensure_output_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path is not None else REPORTS_DIR / f"{grid_id}_{business_type}_选址报告.md"
    path.write_text(
        generate_site_report(
            grid_id,
            business_type,
            result_path=result_path,
            use_llm=use_llm,
            llm_client=llm_client,
            model=model,
        ),
        encoding="utf-8",
    )
    return path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="生成评价网格选址报告。")
    parser.add_argument("--grid-id", default=None, help="评价网格 region_id；不提供时默认使用评分结果第一行。")
    parser.add_argument("--business-type", default="社区便利店", choices=["社区便利店", "轻餐饮"])
    parser.add_argument("--template", action="store_true", help="使用模板生成，不调用千问/DashScope。")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    grid_id = args.grid_id
    if grid_id is None:
        data = load_grid_results()
        if data.empty:
            raise ValueError("网格细筛结果为空，无法生成报告。")
        grid_id = str(data.iloc[0].get("grid_id", data.iloc[0]["region_id"]))
    output_path = export_report(grid_id, args.business_type, use_llm=not args.template)
    print(output_path)


if __name__ == "__main__":
    main()
