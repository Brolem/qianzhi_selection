"""Score active Step 7 grids with default or user-defined profiles."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import (
    get_path,
    get_scoring_templates,
    get_weights,
    load_config,
)


WEIGHT_FIELDS = [
    "traffic_accessibility",
    "consumption_potential",
    "employment_customer_proxy",
    "synergy_score",
    "competition_pressure",
    "business_atmosphere",
]
BASE_METRIC_FIELDS = [
    "traffic_accessibility",
    "consumption_potential",
    "employment_customer_proxy",
    "business_atmosphere",
]
PROFILE_RESULT_FIELDS = [
    "profile_id",
    "profile_name",
    "template_id",
    "profile_competition_score",
    "profile_score",
    "profile_rank",
    "district_profile_rank",
    "profile_main_advantage",
    "profile_main_risk",
    "profile_recommendation_level",
]
DEFAULT_TEMPLATES = {
    "community_retail": {
        "synergy_field": "convenience_synergy_score",
        "competition_field": "convenience_competition_pressure",
    },
    "food_service": {
        "synergy_field": "light_food_synergy_score",
        "competition_field": "light_food_competition_pressure",
    },
}
PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
INACTIVE_ADVANTAGE = "未检测到POI活动"
INACTIVE_RISK = "缺少可用于推荐的POI活动"


@dataclass(frozen=True)
class ScoringProfile:
    """A named six-dimension scoring profile."""

    profile_id: str
    profile_name: str
    template_id: str
    weights: dict[str, float]


def validate_profile(
    profile: ScoringProfile,
    templates: dict[str, dict[str, str]] = DEFAULT_TEMPLATES,
) -> None:
    """Validate profile identity, template and six weights."""
    if not PROFILE_ID_PATTERN.fullmatch(profile.profile_id):
        raise ValueError("profile_id 仅允许小写字母、数字和下划线")
    if not isinstance(profile.profile_name, str) or not profile.profile_name.strip():
        raise ValueError("profile_name 必须为非空文本")
    if profile.template_id not in templates:
        raise ValueError(f"template_id 不受支持：{profile.template_id}")
    if set(profile.weights) != set(WEIGHT_FIELDS):
        raise ValueError(
            "权重字段必须精确包含：" + ", ".join(WEIGHT_FIELDS)
        )

    numeric_weights: list[float] = []
    for field in WEIGHT_FIELDS:
        value = profile.weights[field]
        if isinstance(value, bool):
            raise ValueError(f"权重 {field} 必须为 0-1 的数字")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"权重 {field} 必须为 0-1 的数字") from error
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"权重 {field} 必须位于 0-1")
        numeric_weights.append(number)
    if not math.isclose(sum(numeric_weights), 1.0, abs_tol=0.000001):
        raise ValueError("六项权重总和必须为 1")


def _require_columns(frame: pd.DataFrame, fields: list[str]) -> None:
    missing = [field for field in fields if field not in frame.columns]
    if missing:
        raise ValueError("评分输入缺少字段：" + ", ".join(missing))


def _validated_numeric(frame: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for field in fields:
        original = frame[field]
        numeric = pd.to_numeric(original, errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"评分字段 {field} 必须为数字且不能包含空值")
        if not numeric.between(0, 100).all():
            raise ValueError(f"评分字段 {field} 必须位于 0-100")
        result[field] = numeric.astype(float)
    return result


def _validated_activity(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.copy()
    valid = series.isin([True, False])
    if not valid.all():
        raise ValueError("has_poi_activity 必须为布尔值")
    return series.astype(bool)


def _assign_rank(
    result: pd.DataFrame,
    active: pd.Series,
    rank_field: str,
    district: str | None = None,
) -> None:
    result[rank_field] = pd.Series(pd.NA, index=result.index, dtype="Int64")
    if district is None:
        subset = result.loc[active]
        ordered = subset.sort_values(
            ["profile_score", "poi_total_count", "grid_id"],
            ascending=[False, False, True],
            kind="mergesort",
        )
        result.loc[ordered.index, rank_field] = range(1, len(ordered) + 1)
        return

    for _, subset in result.loc[active].groupby(district, sort=True):
        ordered = subset.sort_values(
            ["profile_score", "poi_total_count", "grid_id"],
            ascending=[False, False, True],
            kind="mergesort",
        )
        result.loc[ordered.index, rank_field] = range(1, len(ordered) + 1)


def _recommendation_levels(ranks: pd.Series, active_count: int) -> pd.Series:
    levels = pd.Series("暂不推荐", index=ranks.index, dtype=object)
    if active_count == 0:
        return levels
    recommended_end = math.ceil(active_count * 0.20)
    cautious_end = math.ceil(active_count * 0.60)
    levels.loc[ranks.notna() & ranks.le(recommended_end)] = "推荐"
    levels.loc[
        ranks.notna()
        & ranks.gt(recommended_end)
        & ranks.le(cautious_end)
    ] = "谨慎推荐"
    return levels


def _build_explanations(
    result: pd.DataFrame,
    numeric: pd.DataFrame,
    synergy_field: str,
    competition_field: str,
    active: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    advantage_values = pd.DataFrame(
        {
            "交通可达性": numeric["traffic_accessibility"],
            "消费潜力": numeric["consumption_potential"],
            "就业客群代理": numeric["employment_customer_proxy"],
            "共生业态匹配": numeric[synergy_field],
            "商业氛围": numeric["business_atmosphere"],
            "竞争压力较低": result["profile_competition_score"],
        },
        index=result.index,
    )
    risk_values = pd.DataFrame(
        {
            "交通可达性不足": 100 - numeric["traffic_accessibility"],
            "消费潜力不足": 100 - numeric["consumption_potential"],
            "就业客群代理不足": 100 - numeric["employment_customer_proxy"],
            "共生业态匹配不足": 100 - numeric[synergy_field],
            "商业氛围不足": 100 - numeric["business_atmosphere"],
            "竞争压力较高": numeric[competition_field],
        },
        index=result.index,
    )
    advantages = advantage_values.idxmax(axis=1)
    risks = risk_values.idxmax(axis=1)
    advantages.loc[~active] = INACTIVE_ADVANTAGE
    risks.loc[~active] = INACTIVE_RISK
    return advantages, risks


def score_profile(
    scoring_input: pd.DataFrame,
    profile: ScoringProfile,
    templates: dict[str, dict[str, str]] = DEFAULT_TEMPLATES,
) -> pd.DataFrame:
    """Score all rows while excluding inactive grids from rankings."""
    validate_profile(profile, templates)
    template = templates[profile.template_id]
    synergy_field = template["synergy_field"]
    competition_field = template["competition_field"]
    required = [
        "grid_id",
        "district_name",
        "poi_total_count",
        "has_poi_activity",
        *BASE_METRIC_FIELDS,
        synergy_field,
        competition_field,
    ]
    _require_columns(scoring_input, required)
    if scoring_input["grid_id"].duplicated().any():
        duplicates = sorted(
            scoring_input.loc[
                scoring_input["grid_id"].duplicated(keep=False),
                "grid_id",
            ]
            .astype(str)
            .unique()
            .tolist()
        )
        raise ValueError("评分输入存在重复网格：" + ", ".join(duplicates))

    poi_total = pd.to_numeric(scoring_input["poi_total_count"], errors="coerce")
    if poi_total.isna().any() or poi_total.lt(0).any():
        raise ValueError("poi_total_count 必须为非负数字")
    active = _validated_activity(scoring_input["has_poi_activity"])
    numeric = _validated_numeric(
        scoring_input,
        [*BASE_METRIC_FIELDS, synergy_field, competition_field],
    )

    result = scoring_input.copy()
    result["profile_id"] = profile.profile_id
    result["profile_name"] = profile.profile_name.strip()
    result["template_id"] = profile.template_id
    result["profile_competition_score"] = 100.0 - numeric[competition_field]
    result["profile_score"] = (
        numeric["traffic_accessibility"]
        * float(profile.weights["traffic_accessibility"])
        + numeric["consumption_potential"]
        * float(profile.weights["consumption_potential"])
        + numeric["employment_customer_proxy"]
        * float(profile.weights["employment_customer_proxy"])
        + numeric[synergy_field]
        * float(profile.weights["synergy_score"])
        + result["profile_competition_score"]
        * float(profile.weights["competition_pressure"])
        + numeric["business_atmosphere"]
        * float(profile.weights["business_atmosphere"])
    )
    result.loc[~active, "profile_score"] = 0.0
    _assign_rank(result, active, "profile_rank")
    _assign_rank(
        result,
        active,
        "district_profile_rank",
        district="district_name",
    )
    advantages, risks = _build_explanations(
        result,
        numeric,
        synergy_field,
        competition_field,
        active,
    )
    result["profile_main_advantage"] = advantages
    result["profile_main_risk"] = risks
    result["profile_recommendation_level"] = _recommendation_levels(
        result["profile_rank"],
        int(active.sum()),
    )
    return result


def build_default_grid_result(
    scoring_input: pd.DataFrame,
    profiles: dict[str, ScoringProfile],
    templates: dict[str, dict[str, str]] = DEFAULT_TEMPLATES,
) -> pd.DataFrame:
    """Append independent convenience and light-food result columns."""
    required_profiles = {"convenience", "light_food"}
    if set(profiles) != required_profiles:
        raise ValueError("默认评分方案必须精确包含 convenience 和 light_food")
    result = scoring_input.copy()
    rename_suffixes = {
        "profile_competition_score": "competition_score",
        "profile_score": "score",
        "profile_rank": "rank",
        "district_profile_rank": "district_rank",
        "profile_main_advantage": "main_advantage",
        "profile_main_risk": "main_risk",
        "profile_recommendation_level": "recommendation_level",
    }
    for profile_id in ["convenience", "light_food"]:
        scored = score_profile(scoring_input, profiles[profile_id], templates)
        for source, suffix in rename_suffixes.items():
            result[f"{profile_id}_{suffix}"] = scored[source]
    return result


def build_profile_district_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Summarize one profile, using active grids for score statistics."""
    _require_columns(
        scored,
        [
            "district_name",
            "grid_id",
            "poi_total_count",
            "has_poi_activity",
            "profile_score",
            "district_profile_rank",
        ],
    )
    rows: list[dict[str, Any]] = []
    for district_name, group in scored.groupby("district_name", sort=True):
        active = group[group["has_poi_activity"].astype(bool)]
        top_grid_id: str | None = None
        average_score: float | None = None
        if not active.empty:
            top = active.sort_values(
                ["district_profile_rank", "grid_id"],
                ascending=[True, True],
                kind="mergesort",
            ).iloc[0]
            top_grid_id = str(top["grid_id"])
            average_score = float(active["profile_score"].mean())
        rows.append(
            {
                "district_name": district_name,
                "grid_count": int(len(group)),
                "active_grid_count": int(len(active)),
                "avg_profile_score": average_score,
                "top_profile_grid_id": top_grid_id,
                "poi_total_count": int(
                    pd.to_numeric(group["poi_total_count"], errors="raise").sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_default_district_summary(
    grid_result: pd.DataFrame,
) -> pd.DataFrame:
    """Build one district table for both default profiles."""
    base_fields = [
        "district_name",
        "grid_id",
        "poi_total_count",
        "has_poi_activity",
    ]
    summaries: dict[str, pd.DataFrame] = {}
    for profile_id in ["convenience", "light_food"]:
        profile_frame = grid_result[
            [
                *base_fields,
                f"{profile_id}_score",
                f"{profile_id}_district_rank",
            ]
        ].rename(
            columns={
                f"{profile_id}_score": "profile_score",
                f"{profile_id}_district_rank": "district_profile_rank",
            }
        )
        summaries[profile_id] = build_profile_district_summary(profile_frame)

    convenience = summaries["convenience"].rename(
        columns={
            "avg_profile_score": "avg_convenience_score",
            "top_profile_grid_id": "top_convenience_grid_id",
        }
    )
    food = summaries["light_food"][
        [
            "district_name",
            "avg_profile_score",
            "top_profile_grid_id",
        ]
    ].rename(
        columns={
            "avg_profile_score": "avg_light_food_score",
            "top_profile_grid_id": "top_light_food_grid_id",
        }
    )
    return convenience.merge(food, on="district_name", validate="one_to_one")


def _format_weights(profile: ScoringProfile) -> str:
    labels = {
        "traffic_accessibility": "交通可达性",
        "consumption_potential": "消费潜力",
        "employment_customer_proxy": "就业客群代理",
        "synergy_score": "共生业态",
        "competition_pressure": "低竞争得分",
        "business_atmosphere": "商业氛围",
    }
    return "、".join(
        f"{labels[field]} {profile.weights[field]:.0%}"
        for field in WEIGHT_FIELDS
    )


def _append_top_rows(
    lines: list[str],
    scored: pd.DataFrame,
    rank_field: str,
    score_field: str,
    limit: int,
) -> None:
    top = scored[scored[rank_field].notna()].sort_values(rank_field).head(limit)
    for row in top.itertuples(index=False):
        lines.append(
            f"- {getattr(row, rank_field)}. {row.grid_id}（{row.district_name}，"
            f"{getattr(row, score_field):.2f} 分）"
        )


def build_default_report(
    grid_result: pd.DataFrame,
    profiles: dict[str, ScoringProfile],
) -> str:
    """Build the default two-profile recommendation report."""
    lines = [
        "# Step 8 网格评分与推荐摘要",
        "",
        "## 默认评分方案",
        "",
        f"- 社区便利店：{_format_weights(profiles['convenience'])}。",
        f"- 轻餐饮：{_format_weights(profiles['light_food'])}。",
        "- 默认权重为比赛原型的业务经验设定，不代表真实经营数据训练结果。",
        "- 竞争维度按 `100 - competition_pressure` 转换为低竞争得分。",
        "",
    ]
    for profile_id, title in [
        ("convenience", "社区便利店全局 Top 10"),
        ("light_food", "轻餐饮全局 Top 10"),
    ]:
        lines.extend([f"## {title}", ""])
        _append_top_rows(
            lines,
            grid_result,
            f"{profile_id}_rank",
            f"{profile_id}_score",
            10,
        )
        lines.append("")

    for district_name in sorted(grid_result["district_name"].astype(str).unique()):
        lines.extend([f"## {district_name} Top 5", ""])
        district = grid_result[grid_result["district_name"].eq(district_name)]
        for profile_id, title in [
            ("convenience", "社区便利店"),
            ("light_food", "轻餐饮"),
        ]:
            lines.append(f"### {title}")
            lines.append("")
            _append_top_rows(
                lines,
                district,
                f"{profile_id}_district_rank",
                f"{profile_id}_score",
                5,
            )
            lines.append("")

    convenience_top = set(
        grid_result.loc[
            grid_result["convenience_rank"].notna()
            & grid_result["convenience_rank"].le(10),
            "grid_id",
        ]
    )
    food_top = set(
        grid_result.loc[
            grid_result["light_food_rank"].notna()
            & grid_result["light_food_rank"].le(10),
            "grid_id",
        ]
    )
    inactive_count = int((~grid_result["has_poi_activity"].astype(bool)).sum())
    lines.extend(
        [
            "## 结果说明",
            "",
            f"- 两类全局 Top 10 重合网格：{len(convenience_top & food_top)} 个。",
            f"- 无 POI 活动网格：{inactive_count} 个；综合得分固定为 0，排名留空。",
            "- 可通过 `python -m src.modeling.scoring_model --help` 查看自定义权重参数。",
            "- 自定义方案使用现有社区零售型或餐饮服务型指标模板，不等同于新增专属业态数据。",
            "- 结果仅支持当前关键词 POI 样本统一口径下的相对排序。",
            "- 结果不是盈利、租金、客流或营收预测，也不是门牌号级推荐。",
            "",
        ]
    )
    return "\n".join(lines)


def build_custom_report(
    scored: pd.DataFrame,
    profile: ScoringProfile,
) -> str:
    """Build a report for one custom profile."""
    lines = [
        f"# {profile.profile_name}评分摘要",
        "",
        f"- 方案标识：`{profile.profile_id}`",
        f"- 指标模板：`{profile.template_id}`",
        f"- 六维权重：{_format_weights(profile)}。",
        "",
        "## 全局 Top 10",
        "",
    ]
    _append_top_rows(lines, scored, "profile_rank", "profile_score", 10)
    lines.append("")
    for district_name in sorted(scored["district_name"].astype(str).unique()):
        lines.extend([f"## {district_name} Top 5", ""])
        district = scored[scored["district_name"].eq(district_name)]
        _append_top_rows(
            lines,
            district,
            "district_profile_rank",
            "profile_score",
            5,
        )
        lines.append("")
    lines.extend(
        [
            "## 数据边界",
            "",
            "- 自定义权重改变六维指标的相对贡献，不增加新的 POI 或经营数据。",
            "- 结果仅支持当前关键词 POI 样本统一口径下的相对排序。",
            "- 无 POI 活动网格综合得分为 0，排名留空。",
            "- 结果不是盈利、租金、客流或营收预测，也不是门牌号级推荐。",
            "",
        ]
    )
    return "\n".join(lines)


def _write_temp_text(target: Path, content: str, encoding: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        newline="",
        delete=False,
        dir=target.parent,
        suffix=".tmp",
    ) as file:
        file.write(content)
        return Path(file.name)


def build_profile_metadata(
    profiles: list[ScoringProfile] | tuple[ScoringProfile, ...],
) -> dict[str, Any]:
    """Build the stable structured metadata document for scoring profiles."""
    return {
        "schema_version": 1,
        "profiles": [
            {
                "profile_id": profile.profile_id,
                "profile_name": profile.profile_name.strip(),
                "template_id": profile.template_id,
                "weights": {
                    field: float(profile.weights[field])
                    for field in WEIGHT_FIELDS
                },
            }
            for profile in profiles
        ],
    }


def write_profile_outputs_atomically(
    grid_result: pd.DataFrame,
    district_summary: pd.DataFrame,
    report: str,
    metadata: dict[str, Any],
    grid_path: str | Path,
    district_path: str | Path,
    report_path: str | Path,
    metadata_path: str | Path,
) -> dict[str, Path]:
    """Replace four related profile outputs and restore all on failure."""
    targets = {
        "grid": Path(grid_path),
        "district": Path(district_path),
        "report": Path(report_path),
        "metadata": Path(metadata_path),
    }
    contents = {
        "grid": (grid_result.to_csv(index=False), "utf-8-sig"),
        "district": (district_summary.to_csv(index=False), "utf-8-sig"),
        "report": (report, "utf-8"),
        "metadata": (
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            "utf-8",
        ),
    }
    temporary = {
        key: _write_temp_text(targets[key], *contents[key])
        for key in targets
    }
    previous = {
        key: targets[key].read_bytes() if targets[key].exists() else None
        for key in targets
    }
    try:
        for key in ["grid", "district", "report", "metadata"]:
            os.replace(temporary[key], targets[key])
    except Exception:
        for key, target in targets.items():
            if previous[key] is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous[key])
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
    return targets


def run_custom_profile(
    scoring_input: pd.DataFrame,
    profile: ScoringProfile,
    results_dir: str | Path,
    templates: dict[str, dict[str, str]] = DEFAULT_TEMPLATES,
) -> dict[str, Path]:
    """Score and save one custom profile in an isolated directory."""
    scored = score_profile(scoring_input, profile, templates)
    summary = build_profile_district_summary(scored)
    report = build_custom_report(scored, profile)
    output_dir = Path(results_dir) / "custom_profiles" / profile.profile_id
    return write_profile_outputs_atomically(
        scored,
        summary,
        report,
        build_profile_metadata([profile]),
        output_dir / "grid_score_result.csv",
        output_dir / "district_summary_result.csv",
        output_dir / "recommendation_summary.md",
        output_dir / "profile_metadata.json",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the Step 8 command-line parser."""
    parser = argparse.ArgumentParser(
        description="生成默认评分结果，或运行一个完整的自定义六维权重方案。"
    )
    parser.add_argument("--profile-id")
    parser.add_argument("--profile-name")
    parser.add_argument("--template")
    parser.add_argument("--traffic-weight", type=float)
    parser.add_argument("--consumption-weight", type=float)
    parser.add_argument("--employment-weight", type=float)
    parser.add_argument("--synergy-weight", type=float)
    parser.add_argument("--competition-weight", type=float)
    parser.add_argument("--atmosphere-weight", type=float)
    return parser


def profile_from_args(
    args: argparse.Namespace,
    templates: dict[str, dict[str, str]] = DEFAULT_TEMPLATES,
) -> ScoringProfile | None:
    """Return a validated custom profile or None for default execution."""
    values = {
        "profile_id": args.profile_id,
        "profile_name": args.profile_name,
        "template": args.template,
        "traffic_weight": args.traffic_weight,
        "consumption_weight": args.consumption_weight,
        "employment_weight": args.employment_weight,
        "synergy_weight": args.synergy_weight,
        "competition_weight": args.competition_weight,
        "atmosphere_weight": args.atmosphere_weight,
    }
    provided = [value is not None for value in values.values()]
    if not any(provided):
        return None
    if not all(provided):
        raise ValueError("自定义评分参数必须全部提供")
    profile = ScoringProfile(
        profile_id=str(args.profile_id),
        profile_name=str(args.profile_name),
        template_id=str(args.template),
        weights={
            "traffic_accessibility": float(args.traffic_weight),
            "consumption_potential": float(args.consumption_weight),
            "employment_customer_proxy": float(args.employment_weight),
            "synergy_score": float(args.synergy_weight),
            "competition_pressure": float(args.competition_weight),
            "business_atmosphere": float(args.atmosphere_weight),
        },
    )
    validate_profile(profile, templates)
    return profile


def _default_profiles(config: dict[str, Any]) -> dict[str, ScoringProfile]:
    return {
        "convenience": ScoringProfile(
            profile_id="convenience",
            profile_name="社区便利店",
            template_id="community_retail",
            weights=get_weights(config, "convenience"),
        ),
        "light_food": ScoringProfile(
            profile_id="light_food",
            profile_name="轻餐饮",
            template_id="food_service",
            weights=get_weights(config, "light_food"),
        ),
    }


def validate_formal_scope(
    scoring_input: pd.DataFrame,
    expected_districts: list[str],
) -> None:
    """Validate the real Step 8 input scope before writing formal outputs."""
    if len(scoring_input) != 60:
        raise ValueError(f"Step 8 评分输入应为 60 行，实际为 {len(scoring_input)} 行")
    counts = scoring_input.groupby("district_name").size().to_dict()
    invalid = {
        district: int(counts.get(district, 0))
        for district in expected_districts
        if int(counts.get(district, 0)) != 20
    }
    if invalid:
        details = "，".join(
            f"{district}={count}" for district, count in invalid.items()
        )
        raise ValueError(f"每个目标区县应有 20 行，实际为：{details}")
    if set(scoring_input["district_name"].astype(str)) != set(expected_districts):
        raise ValueError("Step 8 评分输入区县集合与配置不一致")


def run_default_scoring(
    scoring_input: pd.DataFrame,
    profiles: dict[str, ScoringProfile],
    templates: dict[str, dict[str, str]],
    results_dir: str | Path,
) -> dict[str, Path]:
    """Build and save both default profile outputs."""
    grid_result = build_default_grid_result(scoring_input, profiles, templates)
    district_summary = build_default_district_summary(grid_result)
    report = build_default_report(grid_result, profiles)
    output_dir = Path(results_dir)
    ordered_profiles = [
        profiles["convenience"],
        profiles["light_food"],
    ]
    return write_profile_outputs_atomically(
        grid_result,
        district_summary,
        report,
        build_profile_metadata(ordered_profiles),
        output_dir / "grid_stage_score_result.csv",
        output_dir / "district_summary_result.csv",
        output_dir / "recommendation_summary.md",
        output_dir / "profile_metadata.json",
    )


def main() -> None:
    """Run default Step 8 scoring or one custom profile."""
    args = build_parser().parse_args()
    config = load_config()
    templates = get_scoring_templates(config)
    custom_profile = profile_from_args(args, templates)
    processed_dir = get_path("processed_dir", config)
    results_dir = get_path("results_dir", config)
    input_path = processed_dir / "grid_scoring_input.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"Step 7 评分输入不存在：{input_path}")
    scoring_input = pd.read_csv(input_path, dtype={"adcode": str})
    validate_formal_scope(
        scoring_input,
        list(config["target_districts"]["first_version"]),
    )

    if custom_profile is None:
        outputs = run_default_scoring(
            scoring_input,
            _default_profiles(config),
            templates,
            results_dir,
        )
        print("Default Step 8 scoring completed")
    else:
        outputs = run_custom_profile(
            scoring_input,
            custom_profile,
            results_dir,
            templates,
        )
        print(f"Custom profile completed: {custom_profile.profile_id}")
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
