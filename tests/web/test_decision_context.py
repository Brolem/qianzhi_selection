import unittest
from types import SimpleNamespace

import pandas as pd

from src.web.decision_context import (
    DECISION_GRID_KEY,
    DECISION_PROFILE_KEY,
    grid_default_index,
    profile_default_index,
    save_decision_context,
)


class DecisionContextTests(unittest.TestCase):
    def test_saved_profile_and_grid_drive_page_default_indices(self):
        state = {}
        save_decision_context(
            state,
            profile_id="light_food",
            grid_id="grid_2",
        )
        specs = {
            "默认｜社区便利店": SimpleNamespace(profile_id="convenience"),
            "默认｜轻餐饮": SimpleNamespace(profile_id="light_food"),
        }
        rows = pd.DataFrame(
            [
                {"grid_id": "grid_1"},
                {"grid_id": "grid_2"},
                {"grid_id": "grid_3"},
            ]
        )

        self.assertEqual(state[DECISION_PROFILE_KEY], "light_food")
        self.assertEqual(state[DECISION_GRID_KEY], "grid_2")
        self.assertEqual(profile_default_index(specs, state), 1)
        self.assertEqual(grid_default_index(rows, state), 1)

    def test_missing_or_stale_context_falls_back_to_first_option(self):
        specs = {
            "默认｜社区便利店": SimpleNamespace(profile_id="convenience"),
        }
        rows = pd.DataFrame([{"grid_id": "grid_1"}])

        self.assertEqual(profile_default_index(specs, {}), 0)
        self.assertEqual(
            profile_default_index(
                specs,
                {DECISION_PROFILE_KEY: "removed_profile"},
            ),
            0,
        )
        self.assertEqual(
            grid_default_index(
                rows,
                {DECISION_GRID_KEY: "removed_grid"},
            ),
            0,
        )
