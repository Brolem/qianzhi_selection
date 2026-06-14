"""Interactive weight budgeting and custom scoring services."""

from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.core.config import get_weights, load_config
from src.modeling.scoring_model import (
    WEIGHT_FIELDS,
    ScoringProfile,
    run_custom_profile,
    score_profile,
)


PERCENT_QUANTUM = Decimal("0.01")
PERCENT_TOTAL = Decimal("100.00")
WEIGHT_LABELS = {
    "traffic_accessibility": "交通可达性",
    "consumption_potential": "消费潜力",
    "employment_customer_proxy": "就业客群代理",
    "synergy_score": "共生业态",
    "competition_pressure": "竞争压力",
    "business_atmosphere": "商业氛围",
}
EQUAL_PERCENTAGES = {
    "traffic_accessibility": 16.67,
    "consumption_potential": 16.67,
    "employment_customer_proxy": 16.67,
    "synergy_score": 16.67,
    "competition_pressure": 16.66,
    "business_atmosphere": 16.66,
}


def _percentage_decimals(values: dict[str, Any]) -> dict[str, Decimal]:
    if set(values) != set(WEIGHT_FIELDS):
        raise ValueError("权重字段必须精确包含：" + ", ".join(WEIGHT_FIELDS))
    result: dict[str, Decimal] = {}
    for field in WEIGHT_FIELDS:
        if isinstance(values[field], bool):
            raise ValueError(f"{WEIGHT_LABELS[field]}必须为非负数字")
        try:
            number = Decimal(str(values[field]))
        except Exception as exc:
            raise ValueError(
                f"{WEIGHT_LABELS[field]}必须为非负数字"
            ) from exc
        if not number.is_finite() or number < 0:
            raise ValueError(f"{WEIGHT_LABELS[field]}必须为非负数字")
        if number > PERCENT_TOTAL:
            raise ValueError(f"{WEIGHT_LABELS[field]}不能超过 100")
        result[field] = number.quantize(PERCENT_QUANTUM)
    return result


def percentage_total(values: dict[str, Any]) -> Decimal:
    """Return the exact two-decimal percentage total."""
    return sum(_percentage_decimals(values).values(), Decimal("0.00"))


def normalize_percentages(values: dict[str, Any]) -> dict[str, float]:
    """Normalize nonnegative values to exactly 100.00 percentage points."""
    decimals = _percentage_decimals(values)
    total = sum(decimals.values(), Decimal("0.00"))
    if total == 0:
        raise ValueError("六项权重不能全部为 0")

    target_units = 10_000
    floors: dict[str, int] = {}
    remainders: dict[str, Decimal] = {}
    for field in WEIGHT_FIELDS:
        quota = decimals[field] / total * target_units
        floor_units = int(quota.to_integral_value(rounding=ROUND_FLOOR))
        floors[field] = floor_units
        remainders[field] = quota - floor_units

    remaining = target_units - sum(floors.values())
    field_order = {field: index for index, field in enumerate(WEIGHT_FIELDS)}
    ranked = sorted(
        WEIGHT_FIELDS,
        key=lambda field: (-remainders[field], field_order[field]),
    )
    for field in ranked[:remaining]:
        floors[field] += 1
    return {
        field: float(Decimal(floors[field]) / Decimal("100"))
        for field in WEIGHT_FIELDS
    }


def weight_preset_percentages(
    profile_id: str,
    config: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Return one configured default profile as exact percentages."""
    cfg = config if config is not None else load_config()
    weights = get_weights(cfg, profile_id)
    return {
        field: float(
            (Decimal(str(weights[field])) * 100).quantize(PERCENT_QUANTUM)
        )
        for field in WEIGHT_FIELDS
    }


def profile_from_percentages(
    profile_id: str,
    profile_name: str,
    template_id: str,
    percentages: dict[str, Any],
    *,
    normalize: bool,
) -> ScoringProfile:
    """Build a validated backend profile from UI percentage values."""
    actual = (
        normalize_percentages(percentages)
        if normalize
        else {
            field: float(value)
            for field, value in _percentage_decimals(percentages).items()
        }
    )
    if not normalize and percentage_total(actual) != PERCENT_TOTAL:
        raise ValueError("保存方案时六项权重合计必须为 100.00")
    return ScoringProfile(
        profile_id=profile_id,
        profile_name=profile_name,
        template_id=template_id,
        weights={
            field: float(
                (Decimal(str(actual[field])) / 100).quantize(
                    Decimal("0.0001")
                )
            )
            for field in WEIGHT_FIELDS
        },
    )


def score_custom_preview(
    scoring_input: pd.DataFrame,
    profile: ScoringProfile,
) -> pd.DataFrame:
    """Score an in-memory custom profile without writing output files."""
    return score_profile(scoring_input, profile)


def save_custom_profile(
    scoring_input: pd.DataFrame,
    *,
    profile_id: str,
    profile_name: str,
    template_id: str,
    percentages: dict[str, Any],
    results_dir: str | Path,
    runner: Callable[..., dict[str, Path]] = run_custom_profile,
) -> dict[str, Path]:
    """Save one new custom profile without overwriting an existing id."""
    profile = profile_from_percentages(
        profile_id,
        profile_name,
        template_id,
        percentages,
        normalize=False,
    )
    output_dir = Path(results_dir) / "custom_profiles" / profile.profile_id
    if output_dir.exists():
        raise FileExistsError(f"自定义评分方案已存在：{output_dir}")
    return runner(scoring_input, profile, Path(results_dir))
