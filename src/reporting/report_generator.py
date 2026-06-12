"""Generate v2 intelligent site-selection reports with DeepSeek or templates."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.config import get_path, load_config
from src.profile_catalog import (
    ResultProfileSpec,
    profile_specs_by_id,
)


REPORTS_DIR = get_path("reports_dir")
PROCESSED_DIR = get_path("processed_dir")
MACRO_PATH = PROCESSED_DIR / "official" / "macro_clean.csv"
EMPLOYMENT_PATH = PROCESSED_DIR / "official" / "employment_clean.csv"
REPORT_HEADINGS = [
    "## 一、评价网格基本信息",
    "## 二、适配业态与推荐等级",
    "## 三、交通可达性分析",
    "## 四、消费潜力分析",
    "## 五、就业/办公客群代理分析",
    "## 六、共生业态分析",
    "## 七、竞争压力分析",
    "## 八、商业氛围与权重方案",
    "## 九、主要优势与风险",
    "## 十、经营建议",
    "## 十一、数据来源与限制说明",
]
WEIGHT_LABELS = {
    "traffic_accessibility": "交通可达性",
    "consumption_potential": "消费潜力",
    "employment_customer_proxy": "就业/办公客群代理",
    "synergy_score": "共生业态",
    "competition_pressure": "低竞争得分",
    "business_atmosphere": "商业氛围",
}


class MissingDeepSeekConfigError(RuntimeError):
    """Raised when required DeepSeek configuration is unavailable."""


class InvalidReportContentError(RuntimeError):
    """Raised when model output is empty or misses required sections."""


@dataclass(frozen=True)
class ReportGenerationResult:
    """One generated report plus its non-business execution metadata."""

    content: str
    mode: str
    model: str | None
    used_fallback: bool


def _llm_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    values = cfg.get("llm")
    if not isinstance(values, dict):
        raise KeyError("config.yaml 缺少 llm")
    if values.get("provider") != "deepseek":
        raise ValueError("config.yaml 中 llm.provider 必须为 deepseek")
    return values


def create_deepseek_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
    config: dict[str, Any] | None = None,
) -> Any:
    """Create the OpenAI-compatible DeepSeek client."""
    values = _llm_config(config)
    resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_key:
        raise MissingDeepSeekConfigError(
            "缺少 DEEPSEEK_API_KEY，无法调用 DeepSeek 生成报告。"
        )
    resolved_base_url = (
        base_url
        or os.getenv("DEEPSEEK_BASE_URL")
        or str(values["base_url"])
    )
    resolved_timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else os.getenv("DEEPSEEK_TIMEOUT_SECONDS", values["timeout_seconds"])
    )
    resolved_retries = int(
        max_retries
        if max_retries is not None
        else os.getenv(
            "DEEPSEEK_PRIMARY_MAX_RETRIES",
            values["primary_max_retries"],
        )
    )
    from openai import OpenAI

    return OpenAI(
        api_key=resolved_key,
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        max_retries=resolved_retries,
    )


def load_official_data_context(
    macro_path: str | Path = MACRO_PATH,
    employment_path: str | Path = EMPLOYMENT_PATH,
) -> dict[str, str]:
    """Validate and describe the current official-data geographic scope."""
    macro_file = Path(macro_path)
    employment_file = Path(employment_path)
    for path in [macro_file, employment_file]:
        if not path.exists():
            raise FileNotFoundError(f"官方背景数据不存在：{path}")
    macro = pd.read_csv(macro_file, dtype={"area_code": str})
    employment = pd.read_csv(employment_file, dtype={"region_id": str})
    if "area_code" not in macro.columns:
        raise KeyError(f"{macro_file} 缺少字段：area_code")
    for field in ["region_id", "region_name"]:
        if field not in employment.columns:
            raise KeyError(f"{employment_file} 缺少字段：{field}")
    macro_codes = sorted(macro["area_code"].dropna().astype(str).unique())
    employment_codes = sorted(
        employment["region_id"].dropna().astype(str).unique()
    )
    if macro_codes != ["520000"] or employment_codes != ["520000"]:
        raise ValueError(
            "官方宏观与就业数据当前必须保持贵州省级范围 520000"
        )
    return {
        "scope": "贵州省级",
        "macro_source": str(macro_file),
        "employment_source": str(employment_file),
        "usage": "只作贵州省整体市场背景与数据适用边界说明，不参与网格评分，也不用于制造区县差异。",
    }


def _required_fields(profile: ResultProfileSpec) -> list[str]:
    return [
        "grid_id",
        "district_name",
        "centroid_lon",
        "centroid_lat",
        "area_km2",
        "poi_total_count",
        "poi_category_coverage",
        "has_poi_activity",
        "traffic_accessibility",
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        profile.synergy_field,
        profile.competition_pressure_field,
        profile.competition_score_field,
        profile.score_field,
        profile.rank_field,
        profile.district_rank_field,
        profile.advantage_field,
        profile.risk_field,
        profile.level_field,
    ]


def load_profile_results(profile: ResultProfileSpec) -> pd.DataFrame:
    """Load and validate one Step 8 profile result."""
    if not profile.result_path.exists():
        raise FileNotFoundError(f"评分结果不存在：{profile.result_path}")
    frame = pd.read_csv(profile.result_path, dtype={"adcode": str})
    missing = [field for field in _required_fields(profile) if field not in frame]
    if missing:
        raise KeyError(
            f"{profile.result_path} 缺少字段：{', '.join(missing)}"
        )
    if frame["grid_id"].duplicated().any():
        raise ValueError(f"{profile.result_path} 存在重复 grid_id")
    return frame


def active_profile_results(profile: ResultProfileSpec) -> pd.DataFrame:
    """Return active, ranked grids ordered by profile rank."""
    frame = load_profile_results(profile)
    activity = frame["has_poi_activity"]
    if activity.dtype != bool:
        if not activity.isin([True, False]).all():
            raise ValueError(
                f"{profile.result_path} 中 has_poi_activity 必须为布尔值"
            )
        activity = activity.astype(bool)
    ranks = pd.to_numeric(frame[profile.rank_field], errors="coerce")
    active = frame[activity & ranks.notna()].copy()
    active[profile.rank_field] = ranks[activity & ranks.notna()]
    return active.sort_values(
        [profile.rank_field, "grid_id"],
        kind="mergesort",
    ).reset_index(drop=True)


def _find_active_record(
    profile: ResultProfileSpec,
    grid_id: str,
) -> dict[str, Any]:
    frame = load_profile_results(profile)
    matched = frame[frame["grid_id"].astype(str).eq(str(grid_id))]
    if matched.empty:
        raise KeyError(f"未找到评价网格：{grid_id}")
    record = matched.iloc[0]
    active = record["has_poi_activity"]
    if isinstance(active, str):
        active = active.strip().lower() == "true"
    if not bool(active) or pd.isna(record[profile.rank_field]):
        raise ValueError(f"评价网格 {grid_id} 无 POI 活动，不能生成智能报告")
    return record.to_dict()


def _value(record: Mapping[str, Any], field: str) -> Any:
    value = record[field]
    if pd.isna(value):
        raise ValueError(f"评分记录字段 {field} 不能为空")
    if hasattr(value, "item"):
        return value.item()
    return value


def build_report_payload(
    record: Mapping[str, Any],
    profile: ResultProfileSpec,
    official_context: Mapping[str, str],
) -> dict[str, Any]:
    """Build the exact structured payload used by template and LLM reports."""
    return {
        "profile": {
            "profile_id": profile.profile_id,
            "profile_name": profile.profile_name,
            "template_id": profile.template_id,
            "weights": profile.weights,
        },
        "grid": {
            field: _value(record, field)
            for field in [
                "grid_id",
                "district_name",
                "centroid_lon",
                "centroid_lat",
                "area_km2",
                "poi_total_count",
                "poi_category_coverage",
            ]
        },
        "metrics": {
            "traffic_accessibility": _value(
                record,
                "traffic_accessibility",
            ),
            "consumption_potential": _value(
                record,
                "consumption_potential",
            ),
            "employment_customer_proxy": _value(
                record,
                "employment_customer_proxy",
            ),
            "synergy_score": _value(record, profile.synergy_field),
            "competition_pressure": _value(
                record,
                profile.competition_pressure_field,
            ),
            "competition_score": _value(
                record,
                profile.competition_score_field,
            ),
            "business_atmosphere": _value(record, "business_atmosphere"),
        },
        "recommendation": {
            "score": _value(record, profile.score_field),
            "global_rank": _value(record, profile.rank_field),
            "district_rank": _value(record, profile.district_rank_field),
            "level": _value(record, profile.level_field),
            "main_advantage": _value(record, profile.advantage_field),
            "main_risk": _value(record, profile.risk_field),
        },
        "official_data": dict(official_context),
        "method_boundaries": [
            "employment_customer_proxy 是由写字楼、商场、学校、餐饮等 POI 构成的就业/办公客群代理，不是真实就业人口密度。",
            "结果只支持当前关键词 POI 样本统一口径下的相对评价，不代表完整设施总量。",
            "结果不是租金、客流、营收或盈利预测，也不是门牌号级推荐。",
        ],
    }


def build_report_prompt(
    record: Mapping[str, Any],
    profile: ResultProfileSpec,
    official_context: Mapping[str, str],
) -> str:
    """Build the strict DeepSeek report prompt."""
    payload = build_report_payload(record, profile, official_context)
    headings = "\n".join(REPORT_HEADINGS)
    return f"""请仅根据结构化输入生成 Markdown 格式的商业智能选址报告。

结构化输入：
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}

必须按以下二级标题原样、依次输出：
{headings}

硬性要求：
1. 不得添加结构化输入之外的事实、数值、地址或经营结论。
2. employment_customer_proxy 只能解释为 POI 构成的就业/办公客群代理，不能解释为真实就业人口或人口密度。
3. 官方数据当前为贵州省级，只作整体市场背景与适用边界，不参与区县或网格评分。
4. 必须说明结果来自关键词 POI 样本统一口径下的相对评价。
5. 不得写成完整设施总量、租金、客流、营收、盈利或门牌号级预测。
6. 语言正式、简洁，适合比赛答辩和项目演示。
""".strip()


def validate_report_content(content: Any) -> str:
    """Require a non-empty report containing every exact heading."""
    if not isinstance(content, str) or not content.strip():
        raise InvalidReportContentError("DeepSeek 返回的报告正文为空")
    missing = [heading for heading in REPORT_HEADINGS if heading not in content]
    if missing:
        raise InvalidReportContentError(
            "DeepSeek 报告缺少规定章节：" + ", ".join(missing)
        )
    return content.strip() + "\n"


def _is_retryable_error(error: BaseException) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code == 404 or status_code == 429:
        return True
    if isinstance(status_code, int) and 500 <= status_code <= 599:
        return True
    try:
        from openai import APIConnectionError, APITimeoutError
    except ImportError:
        return False
    return isinstance(error, (APIConnectionError, APITimeoutError))


def _model_config(
    config: dict[str, Any] | None,
    primary_model: str | None,
    fallback_model: str | None,
) -> tuple[str, str]:
    values = _llm_config(config)
    primary = (
        primary_model
        or os.getenv("DEEPSEEK_PRIMARY_MODEL")
        or str(values["primary_model"])
    )
    fallback = (
        fallback_model
        or os.getenv("DEEPSEEK_FALLBACK_MODEL")
        or str(values["fallback_model"])
    )
    return primary, fallback


def _call_model(
    client: Any,
    model: str,
    prompt: str,
) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是商业选址分析师，只能依据结构化输入生成报告。",
            },
            {"role": "user", "content": prompt},
        ],
        extra_body={"thinking": {"type": "disabled"}},
        temperature=0.2,
        max_tokens=4096,
        stream=False,
    )
    choices = getattr(completion, "choices", None)
    content = (
        choices[0].message.content
        if choices and getattr(choices[0], "message", None)
        else None
    )
    return validate_report_content(content)


def _format_number(value: Any) -> str:
    return f"{float(value):.2f}"


def generate_template_report(
    record: Mapping[str, Any],
    profile: ResultProfileSpec,
    official_context: Mapping[str, str],
) -> str:
    """Generate the deterministic v2 eleven-section report."""
    payload = build_report_payload(record, profile, official_context)
    grid = payload["grid"]
    metrics = payload["metrics"]
    recommendation = payload["recommendation"]
    weights = payload["profile"]["weights"]
    weight_text = "、".join(
        f"{WEIGHT_LABELS[field]} {float(weights[field]) * 100:.0f}%"
        for field in WEIGHT_LABELS
    )
    return f"""# {grid['district_name']} {profile.profile_name}选址报告

{REPORT_HEADINGS[0]}

- 网格标识：`{grid['grid_id']}`
- 所属区县：{grid['district_name']}
- 中心经纬度：{grid['centroid_lon']}，{grid['centroid_lat']}
- 裁剪面积：{_format_number(grid['area_km2'])} 平方公里
- POI 类别覆盖：{grid['poi_category_coverage']} 类
- POI 类别计数合计：{grid['poi_total_count']}

{REPORT_HEADINGS[1]}

当前评分方案为“{profile.profile_name}”，综合得分 {_format_number(recommendation['score'])}，全局排名第 {int(float(recommendation['global_rank']))}，区县排名第 {int(float(recommendation['district_rank']))}，推荐等级为“{recommendation['level']}”。

{REPORT_HEADINGS[2]}

交通可达性得分为 {_format_number(metrics['traffic_accessibility'])}，用于同一 POI 查询口径下的网格相对比较。

{REPORT_HEADINGS[3]}

消费潜力得分为 {_format_number(metrics['consumption_potential'])}，反映当前已接入生活服务设施的相对支撑程度。

{REPORT_HEADINGS[4]}

就业/办公客群代理得分为 {_format_number(metrics['employment_customer_proxy'])}。该指标由写字楼、商场、学校、餐饮等 POI 构成，不是真实就业人口密度。

{REPORT_HEADINGS[5]}

共生业态得分为 {_format_number(metrics['synergy_score'])}，使用 `{profile.synergy_field}` 字段。

{REPORT_HEADINGS[6]}

竞争压力为 {_format_number(metrics['competition_pressure'])}，转换后的低竞争得分为 {_format_number(metrics['competition_score'])}。该结果不代表企业真实经营状态。

{REPORT_HEADINGS[7]}

商业氛围得分为 {_format_number(metrics['business_atmosphere'])}。本方案六维权重为：{weight_text}。

{REPORT_HEADINGS[8]}

主要优势：{recommendation['main_advantage']}。主要风险：{recommendation['main_risk']}。

{REPORT_HEADINGS[9]}

建议将该网格作为实地调研对象，进一步核验现场客流、租金、门店条件、竞品经营状态和停车便利性后再做经营决策。

{REPORT_HEADINGS[10]}

官方宏观与就业数据当前为贵州省级，只作整体市场背景与数据适用边界说明，不参与网格评分，也不用于制造区县差异。网格结果来自关键词 POI 样本统一口径下的相对评价，不代表完整设施总量，不是租金、客流、营收或盈利预测，也不是门牌号级推荐。
"""


def generate_site_report(
    grid_id: str,
    profile: ResultProfileSpec,
    *,
    use_llm: bool = True,
    llm_client: Any | None = None,
    config: dict[str, Any] | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    primary_model: str | None = None,
    fallback_model: str | None = None,
    macro_path: str | Path = MACRO_PATH,
    employment_path: str | Path = EMPLOYMENT_PATH,
) -> ReportGenerationResult:
    """Generate one active-grid report for a default or custom profile."""
    record = _find_active_record(profile, grid_id)
    official_context = load_official_data_context(
        macro_path,
        employment_path,
    )
    if not use_llm:
        return ReportGenerationResult(
            content=generate_template_report(
                record,
                profile,
                official_context,
            ),
            mode="template",
            model=None,
            used_fallback=False,
        )

    client = llm_client or create_deepseek_client(
        api_key=api_key,
        base_url=base_url,
        config=config,
    )
    primary, fallback = _model_config(
        config,
        primary_model,
        fallback_model,
    )
    prompt = build_report_prompt(record, profile, official_context)
    try:
        content = _call_model(client, primary, prompt)
        return ReportGenerationResult(
            content=content,
            mode="deepseek",
            model=primary,
            used_fallback=False,
        )
    except InvalidReportContentError:
        raise
    except Exception as error:
        if not _is_retryable_error(error):
            raise

    content = _call_model(client, fallback, prompt)
    return ReportGenerationResult(
        content=content,
        mode="deepseek",
        model=fallback,
        used_fallback=True,
    )


def export_report(
    report: ReportGenerationResult,
    grid_id: str,
    profile: ResultProfileSpec,
    output_path: str | Path | None = None,
    *,
    reports_dir: str | Path = REPORTS_DIR,
) -> Path:
    """Atomically export one Markdown report without model metadata."""
    target = (
        Path(output_path)
        if output_path is not None
        else Path(reports_dir)
        / profile.profile_id
        / f"{grid_id}_选址报告.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=target.parent,
        suffix=".tmp",
    ) as file:
        file.write(report.content)
        temporary = Path(file.name)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def build_parser() -> argparse.ArgumentParser:
    """Build the Step 10 command-line parser."""
    parser = argparse.ArgumentParser(
        description="生成 v2 DeepSeek 智能选址报告。"
    )
    parser.add_argument("--profile", default="convenience")
    parser.add_argument("--grid-id")
    parser.add_argument(
        "--template",
        action="store_true",
        help="使用规则模板，不调用 DeepSeek。",
    )
    return parser


def main() -> None:
    """Generate and export one profile report."""
    args = build_parser().parse_args()
    specs = profile_specs_by_id()
    if args.profile not in specs:
        raise ValueError(f"评分方案不存在：{args.profile}")
    profile = specs[args.profile]
    grid_id = args.grid_id
    if grid_id is None:
        active = active_profile_results(profile)
        if active.empty:
            raise ValueError(f"评分方案 {profile.profile_id} 没有活跃排名网格")
        grid_id = str(active.iloc[0]["grid_id"])
    report = generate_site_report(
        grid_id,
        profile,
        use_llm=not args.template,
    )
    output = export_report(report, grid_id, profile)
    print(output)


if __name__ == "__main__":
    main()
