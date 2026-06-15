"""Shared Step 8 result-profile discovery for maps and reports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import get_path


RESULTS_DIR = get_path("results_dir")
FIGURES_DIR = get_path("figures_dir")
DEFAULT_RESULT_PATH = RESULTS_DIR / "grid_stage_score_result.csv"
DEFAULT_METADATA_PATH = RESULTS_DIR / "profile_metadata.json"
CUSTOM_PROFILES_DIR = RESULTS_DIR / "custom_profiles"
PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
WEIGHT_FIELDS = [
    "traffic_accessibility",
    "consumption_potential",
    "employment_customer_proxy",
    "synergy_score",
    "competition_pressure",
    "business_atmosphere",
]
TEMPLATE_FIELDS = {
    "community_retail": {
        "synergy_field": "convenience_synergy_score",
        "competition_pressure_field": "convenience_competition_pressure",
    },
    "food_service": {
        "synergy_field": "light_food_synergy_score",
        "competition_pressure_field": "light_food_competition_pressure",
    },
}


@dataclass(frozen=True)
class ResultProfileSpec:
    """Exact result and metric fields for one scoring profile."""

    profile_id: str
    profile_name: str
    template_id: str
    weights: dict[str, float]
    result_path: Path
    metadata_path: Path
    static_html_path: Path | None
    score_field: str
    rank_field: str
    district_rank_field: str
    competition_score_field: str
    competition_pressure_field: str
    advantage_field: str
    risk_field: str
    level_field: str
    synergy_field: str
    demand_proxy_field: str
    market_stage_field: str
    competition_alert_field: str
    diagnosis_summary_field: str


def _validated_weights(value: Any, path: Path, profile_id: str) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != set(WEIGHT_FIELDS):
        raise ValueError(
            f"{path} 中 {profile_id} 的 weights 必须精确包含："
            + ", ".join(WEIGHT_FIELDS)
        )
    result: dict[str, float] = {}
    for field in WEIGHT_FIELDS:
        raw = value[field]
        if isinstance(raw, bool):
            raise ValueError(f"{path} 中 {profile_id}.{field} 必须是数字")
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{path} 中 {profile_id}.{field} 必须是数字"
            ) from exc
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"{path} 中 {profile_id}.{field} 必须位于 0-1")
        result[field] = number
    if abs(sum(result.values()) - 1.0) > 0.000001:
        raise ValueError(f"{path} 中 {profile_id} 的六项权重总和必须为 1")
    return result


def load_profile_metadata(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load and validate one profile metadata document."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"评分方案元数据不存在：{metadata_path}")
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"{metadata_path} 的 schema_version 必须为 1")
    profiles = data.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError(f"{metadata_path} 的 profiles 必须是非空列表")

    result: dict[str, dict[str, Any]] = {}
    for item in profiles:
        if not isinstance(item, dict):
            raise ValueError(f"{metadata_path} 的 profiles 项必须是映射")
        profile_id = item.get("profile_id")
        profile_name = item.get("profile_name")
        template_id = item.get("template_id")
        if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(
            profile_id
        ):
            raise ValueError(f"{metadata_path} 包含无效 profile_id")
        if profile_id in result:
            raise ValueError(f"{metadata_path} 包含重复 profile_id：{profile_id}")
        if not isinstance(profile_name, str) or not profile_name.strip():
            raise ValueError(f"{metadata_path} 中 {profile_id} 缺少 profile_name")
        if template_id not in TEMPLATE_FIELDS:
            raise ValueError(
                f"{metadata_path} 中 {profile_id} 的 template_id 不受支持："
                f"{template_id}"
            )
        result[profile_id] = {
            "profile_id": profile_id,
            "profile_name": profile_name.strip(),
            "template_id": template_id,
            "weights": _validated_weights(
                item.get("weights"),
                metadata_path,
                profile_id,
            ),
        }
    return result


def _default_spec(
    profile_id: str,
    metadata: dict[str, Any],
    result_path: Path,
    metadata_path: Path,
    figures_dir: Path,
) -> ResultProfileSpec:
    fields = TEMPLATE_FIELDS[metadata["template_id"]]
    prefix = "convenience" if profile_id == "convenience" else "light_food"
    html_name = (
        "convenience_grid_map.html"
        if profile_id == "convenience"
        else "light_food_grid_map.html"
    )
    return ResultProfileSpec(
        **metadata,
        result_path=result_path,
        metadata_path=metadata_path,
        static_html_path=figures_dir / html_name,
        score_field=f"{prefix}_score",
        rank_field=f"{prefix}_rank",
        district_rank_field=f"{prefix}_district_rank",
        competition_score_field=f"{prefix}_competition_score",
        competition_pressure_field=fields["competition_pressure_field"],
        advantage_field=f"{prefix}_main_advantage",
        risk_field=f"{prefix}_main_risk",
        level_field=f"{prefix}_recommendation_level",
        synergy_field=fields["synergy_field"],
        demand_proxy_field=f"{prefix}_demand_customer_proxy",
        market_stage_field=f"{prefix}_market_stage",
        competition_alert_field=f"{prefix}_competition_alert",
        diagnosis_summary_field=f"{prefix}_diagnosis_summary",
    )


def default_profile_specs(
    result_path: str | Path = DEFAULT_RESULT_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
    figures_dir: str | Path = FIGURES_DIR,
) -> dict[str, ResultProfileSpec]:
    """Return the two default Step 8 profile specifications."""
    metadata_file = Path(metadata_path)
    metadata = load_profile_metadata(metadata_file)
    expected = {"convenience", "light_food"}
    if set(metadata) != expected:
        raise ValueError(
            f"{metadata_file} 必须精确包含默认方案：convenience, light_food"
        )
    result_file = Path(result_path)
    figures = Path(figures_dir)
    return {
        profile_id: _default_spec(
            profile_id,
            metadata[profile_id],
            result_file,
            metadata_file,
            figures,
        )
        for profile_id in ["convenience", "light_food"]
    }


def _single_csv_value(
    frame: pd.DataFrame,
    field: str,
    path: Path,
) -> str:
    if field not in frame.columns:
        raise KeyError(f"{path} 缺少字段：{field}")
    values = frame[field].dropna().astype(str).unique().tolist()
    if len(values) != 1:
        raise ValueError(f"{path} 的 {field} 必须只有一个非空值")
    return values[0]


def discover_custom_profile_specs(
    custom_profiles_dir: str | Path = CUSTOM_PROFILES_DIR,
) -> dict[str, ResultProfileSpec]:
    """Discover valid custom profile result directories."""
    base = Path(custom_profiles_dir)
    if not base.exists():
        return {}
    result: dict[str, ResultProfileSpec] = {}
    for profile_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        profile_id = profile_dir.name
        result_path = profile_dir / "grid_score_result.csv"
        metadata_path = profile_dir / "profile_metadata.json"
        if not result_path.exists():
            raise FileNotFoundError(f"自定义评分结果不存在：{result_path}")
        metadata = load_profile_metadata(metadata_path)
        if list(metadata) != [profile_id]:
            raise ValueError(
                f"{metadata_path} 必须只包含目录方案标识 {profile_id}"
            )
        item = metadata[profile_id]
        frame = pd.read_csv(result_path, dtype={"adcode": str})
        for field, expected in [
            ("profile_id", profile_id),
            ("profile_name", item["profile_name"]),
            ("template_id", item["template_id"]),
        ]:
            actual = _single_csv_value(frame, field, result_path)
            if actual != expected:
                raise ValueError(
                    f"{result_path} 的 {field}={actual}，"
                    f"与 {profile_id} 元数据不一致"
                )
        template_fields = TEMPLATE_FIELDS[item["template_id"]]
        result[profile_id] = ResultProfileSpec(
            **item,
            result_path=result_path,
            metadata_path=metadata_path,
            static_html_path=None,
            score_field="profile_score",
            rank_field="profile_rank",
            district_rank_field="district_profile_rank",
            competition_score_field="profile_competition_score",
            competition_pressure_field=template_fields[
                "competition_pressure_field"
            ],
            advantage_field="profile_main_advantage",
            risk_field="profile_main_risk",
            level_field="profile_recommendation_level",
            synergy_field=template_fields["synergy_field"],
            demand_proxy_field="profile_demand_customer_proxy",
            market_stage_field="profile_market_stage",
            competition_alert_field="profile_competition_alert",
            diagnosis_summary_field="profile_diagnosis_summary",
        )
    return result


def profile_specs_by_id(
    result_path: str | Path = DEFAULT_RESULT_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
    figures_dir: str | Path = FIGURES_DIR,
    custom_profiles_dir: str | Path = CUSTOM_PROFILES_DIR,
) -> dict[str, ResultProfileSpec]:
    """Return all default and custom profiles keyed by profile_id."""
    specs = default_profile_specs(result_path, metadata_path, figures_dir)
    specs.update(discover_custom_profile_specs(custom_profiles_dir))
    return specs


def available_profile_specs(
    result_path: str | Path = DEFAULT_RESULT_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
    figures_dir: str | Path = FIGURES_DIR,
    custom_profiles_dir: str | Path = CUSTOM_PROFILES_DIR,
) -> dict[str, ResultProfileSpec]:
    """Return user-facing labels mapped to all valid profiles."""
    specs = profile_specs_by_id(
        result_path,
        metadata_path,
        figures_dir,
        custom_profiles_dir,
    )
    result = {
        "默认｜社区便利店": specs.pop("convenience"),
        "默认｜轻餐饮": specs.pop("light_food"),
    }
    for spec in specs.values():
        result[f"自定义｜{spec.profile_name} ({spec.profile_id})"] = spec
    return result
