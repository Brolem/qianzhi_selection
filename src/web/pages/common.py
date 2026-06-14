"""Shared, read-only data helpers for the Streamlit workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.core.config import get_path
from src.core.profile_catalog import ResultProfileSpec, available_profile_specs


PROCESSED_DIR = get_path("processed_dir")
RESULTS_DIR = get_path("results_dir")
TARGET_DISTRICTS_PATH = PROCESSED_DIR / "target_districts.csv"
SPATIAL_GRIDS_PATH = PROCESSED_DIR / "candidate_grids.csv"
POI_COUNTS_PATH = PROCESSED_DIR / "grid_poi_counts.csv"
SCORING_INPUT_PATH = PROCESSED_DIR / "grid_scoring_input.csv"
MACRO_PATH = PROCESSED_DIR / "official" / "macro_clean.csv"
EMPLOYMENT_PATH = PROCESSED_DIR / "official" / "employment_clean.csv"
SCORES_PATH = RESULTS_DIR / "grid_stage_score_result.csv"
DISTRICT_SUMMARY_PATH = RESULTS_DIR / "district_summary_result.csv"


def get_streamlit(st_module: Any | None = None) -> Any:
    """Return an injected Streamlit facade or import the real module."""
    if st_module is not None:
        return st_module
    import streamlit as st

    return st


def load_required_csv(
    path: str | Path,
    required_columns: Iterable[str] = (),
) -> pd.DataFrame:
    """Load one CSV and validate its exact required columns."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"文件不存在：{csv_path}")
    frame = pd.read_csv(csv_path)
    missing = [
        column for column in required_columns if column not in frame.columns
    ]
    if missing:
        raise KeyError(f"{csv_path} 缺少字段：{', '.join(missing)}")
    return frame


def activity_mask(series: pd.Series) -> pd.Series:
    """Normalize the persisted POI activity flag without altering data."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1"})
    )


def load_profile_options(
    profile_specs: dict[str, ResultProfileSpec] | None = None,
) -> dict[str, ResultProfileSpec]:
    """Return all valid default and custom scoring profiles."""
    specs = profile_specs if profile_specs is not None else available_profile_specs()
    if not specs:
        raise ValueError("当前没有可用的评分方案")
    return specs


def select_profile(
    st: Any,
    *,
    profile_specs: dict[str, ResultProfileSpec] | None = None,
    label: str = "评分方案",
    key: str | None = None,
) -> ResultProfileSpec:
    """Render a page-local scoring-profile selector."""
    specs = load_profile_options(profile_specs)
    selected = st.selectbox(label, list(specs), key=key)
    return specs[selected]


def profile_top_rows(
    profile: ResultProfileSpec,
    *,
    district_name: str | None = None,
    limit: int = 10,
) -> pd.DataFrame:
    """Return active profile rows in deterministic rank order."""
    required = [
        "grid_id",
        "district_name",
        "has_poi_activity",
        profile.score_field,
        profile.rank_field,
    ]
    frame = load_required_csv(profile.result_path, required)
    frame = frame.loc[activity_mask(frame["has_poi_activity"])].copy()
    frame[profile.rank_field] = pd.to_numeric(
        frame[profile.rank_field],
        errors="coerce",
    )
    frame = frame.loc[frame[profile.rank_field].notna()]
    if district_name is not None and district_name != "全部":
        frame = frame.loc[
            frame["district_name"].astype(str).eq(district_name)
        ]
    frame["grid_id"] = frame["grid_id"].astype(str)
    return (
        frame.sort_values(
            [profile.rank_field, "grid_id"],
            ascending=[True, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )


def available_districts(profile: ResultProfileSpec) -> list[str]:
    """Return sorted district names represented by active ranked grids."""
    frame = profile_top_rows(profile, limit=10_000)
    return sorted(frame["district_name"].dropna().astype(str).unique())


def display_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Select exact display columns and fail when a required field is absent."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"结果缺少字段：{', '.join(missing)}")
    return frame[columns].copy()
