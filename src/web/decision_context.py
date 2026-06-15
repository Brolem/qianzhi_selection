"""Shared decision context across recommendation, map, and report pages."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import pandas as pd


DECISION_PROFILE_KEY = "decision_context_profile_id"
DECISION_GRID_KEY = "decision_context_grid_id"


def save_decision_context(
    state: MutableMapping[str, Any],
    *,
    profile_id: str,
    grid_id: str,
) -> None:
    """Persist one valid scoring-profile and grid selection."""
    state[DECISION_PROFILE_KEY] = str(profile_id)
    state[DECISION_GRID_KEY] = str(grid_id)


def profile_default_index(
    specs: Mapping[str, Any],
    state: Mapping[str, Any],
) -> int:
    """Resolve a saved profile identifier to a current selector index."""
    saved = str(state.get(DECISION_PROFILE_KEY, ""))
    for index, spec in enumerate(specs.values()):
        if str(spec.profile_id) == saved:
            return index
    return 0


def grid_default_index(
    rows: pd.DataFrame,
    state: Mapping[str, Any],
) -> int:
    """Resolve a saved grid identifier to a current selector index."""
    if "grid_id" not in rows:
        raise KeyError("结果缺少字段：grid_id")
    saved = str(state.get(DECISION_GRID_KEY, ""))
    grid_ids = rows["grid_id"].astype(str).tolist()
    return grid_ids.index(saved) if saved in grid_ids else 0
