"""Derive market-stage and competition diagnostics from existing grid metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


MARKET_STAGE_GAP = "市场空白型"
MARKET_STAGE_CULTIVATION = "待培育型"
MARKET_STAGE_MATURE = "成熟商圈型"
MARKET_STAGE_GENERAL = "一般观察型"
COMPETITION_ALERT = "过度竞争预警"
NO_COMPETITION_ALERT = "未触发过度竞争预警"
INACTIVE_MARKET_STAGE = "无 POI 活动"
INACTIVE_COMPETITION_ALERT = "不参与诊断"

DIAGNOSTIC_RESULT_FIELDS = [
    "profile_demand_customer_proxy",
    "profile_market_stage",
    "profile_competition_alert",
    "profile_diagnosis_summary",
]


@dataclass(frozen=True)
class DiagnosticThresholds:
    """Global low and high cutoffs calculated from active grids."""

    low: dict[str, float]
    high: dict[str, float]


def _require_columns(frame: pd.DataFrame, fields: list[str]) -> None:
    missing = [field for field in fields if field not in frame.columns]
    if missing:
        raise ValueError("市场诊断输入缺少字段：" + ", ".join(missing))


def _validated_activity(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.copy()
    if not series.isin([True, False]).all():
        raise ValueError("has_poi_activity 必须为布尔值")
    return series.astype(bool)


def _validated_numeric(frame: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for field in fields:
        numeric = pd.to_numeric(frame[field], errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"市场诊断字段 {field} 必须为数字且不能包含空值")
        if not numeric.between(0, 100).all():
            raise ValueError(f"市场诊断字段 {field} 必须位于 0-100")
        result[field] = numeric.astype(float)
    return result


def _bands(
    series: pd.Series,
    low_threshold: float,
    high_threshold: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    if np.isclose(low_threshold, high_threshold):
        low = series.lt(low_threshold)
        medium = np.isclose(series, low_threshold)
        high = series.gt(high_threshold)
        return low, pd.Series(medium, index=series.index), high
    low = series.le(low_threshold)
    high = series.ge(high_threshold)
    medium = series.gt(low_threshold) & series.lt(high_threshold)
    return low, medium, high


def diagnose_market(
    frame: pd.DataFrame,
    *,
    synergy_field: str,
    competition_field: str,
) -> tuple[pd.DataFrame, DiagnosticThresholds]:
    """Add global active-grid market diagnostics without changing scores."""
    required = [
        "grid_id",
        "has_poi_activity",
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        synergy_field,
        competition_field,
    ]
    _require_columns(frame, required)
    activity = _validated_activity(frame["has_poi_activity"])
    numeric_fields = [
        "consumption_potential",
        "employment_customer_proxy",
        "business_atmosphere",
        synergy_field,
        competition_field,
    ]
    numeric = _validated_numeric(frame, numeric_fields)
    result = frame.copy()
    result["profile_demand_customer_proxy"] = (
        numeric["consumption_potential"]
        + numeric["employment_customer_proxy"]
    ) / 2.0
    result["profile_market_stage"] = INACTIVE_MARKET_STAGE
    result["profile_competition_alert"] = INACTIVE_COMPETITION_ALERT
    result["profile_diagnosis_summary"] = (
        INACTIVE_MARKET_STAGE + "；" + INACTIVE_COMPETITION_ALERT
    )

    if not activity.any():
        return result, DiagnosticThresholds(low={}, high={})

    diagnostic_fields = [
        "consumption_potential",
        "profile_demand_customer_proxy",
        "business_atmosphere",
        synergy_field,
        competition_field,
    ]
    active_values = pd.DataFrame(
        {
            **{
                field: numeric.loc[activity, field]
                for field in numeric_fields
                if field in diagnostic_fields
            },
            "profile_demand_customer_proxy": result.loc[
                activity,
                "profile_demand_customer_proxy",
            ],
        }
    )[diagnostic_fields]
    low_thresholds = {
        field: float(active_values[field].quantile(1 / 3))
        for field in diagnostic_fields
    }
    high_thresholds = {
        field: float(active_values[field].quantile(2 / 3))
        for field in diagnostic_fields
    }

    bands = {
        field: _bands(
            active_values[field],
            low_thresholds[field],
            high_thresholds[field],
        )
        for field in diagnostic_fields
    }
    low = {field: value[0] for field, value in bands.items()}
    medium = {field: value[1] for field, value in bands.items()}
    high = {field: value[2] for field, value in bands.items()}

    market_gap = (
        high["consumption_potential"]
        & high[synergy_field]
        & medium["business_atmosphere"]
        & ~high[competition_field]
    )
    cultivation = (
        low[competition_field]
        & low["business_atmosphere"]
        & low[synergy_field]
    )
    mature = (
        high["business_atmosphere"]
        & high[synergy_field]
        & high[competition_field]
    )
    over_competition = (
        high["business_atmosphere"]
        & high["profile_demand_customer_proxy"]
        & high[competition_field]
    )

    stages = pd.Series(MARKET_STAGE_GENERAL, index=active_values.index)
    stages.loc[cultivation] = MARKET_STAGE_CULTIVATION
    stages.loc[mature] = MARKET_STAGE_MATURE
    stages.loc[market_gap] = MARKET_STAGE_GAP
    alerts = pd.Series(NO_COMPETITION_ALERT, index=active_values.index)
    alerts.loc[over_competition] = COMPETITION_ALERT

    result.loc[activity, "profile_market_stage"] = stages
    result.loc[activity, "profile_competition_alert"] = alerts
    result.loc[activity, "profile_diagnosis_summary"] = (
        stages.astype(str) + "；" + alerts.astype(str)
    )
    return result, DiagnosticThresholds(
        low=low_thresholds,
        high=high_thresholds,
    )
