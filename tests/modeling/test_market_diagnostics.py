import unittest
from pathlib import Path

import pandas as pd

from src.modeling.market_diagnostics import (
    COMPETITION_ALERT,
    INACTIVE_COMPETITION_ALERT,
    INACTIVE_MARKET_STAGE,
    MARKET_STAGE_CULTIVATION,
    MARKET_STAGE_GENERAL,
    MARKET_STAGE_GAP,
    MARKET_STAGE_MATURE,
    NO_COMPETITION_ALERT,
    diagnose_market,
)


def make_frame(rows):
    return pd.DataFrame(rows)


class MarketDiagnosticsTests(unittest.TestCase):
    def test_diagnosis_assigns_four_stages_and_independent_alert(self):
        frame = make_frame(
            [
                {
                    "grid_id": "gap",
                    "has_poi_activity": True,
                    "consumption_potential": 90,
                    "employment_customer_proxy": 50,
                    "business_atmosphere": 50,
                    "synergy": 90,
                    "competition": 50,
                },
                {
                    "grid_id": "cultivation",
                    "has_poi_activity": True,
                    "consumption_potential": 10,
                    "employment_customer_proxy": 10,
                    "business_atmosphere": 10,
                    "synergy": 10,
                    "competition": 10,
                },
                {
                    "grid_id": "mature_and_alert",
                    "has_poi_activity": True,
                    "consumption_potential": 90,
                    "employment_customer_proxy": 90,
                    "business_atmosphere": 90,
                    "synergy": 90,
                    "competition": 90,
                },
                {
                    "grid_id": "general",
                    "has_poi_activity": True,
                    "consumption_potential": 50,
                    "employment_customer_proxy": 50,
                    "business_atmosphere": 50,
                    "synergy": 50,
                    "competition": 50,
                },
            ]
        )

        result, thresholds = diagnose_market(
            frame,
            synergy_field="synergy",
            competition_field="competition",
        )
        indexed = result.set_index("grid_id")

        self.assertEqual(
            indexed["profile_market_stage"].to_dict(),
            {
                "gap": MARKET_STAGE_GAP,
                "cultivation": MARKET_STAGE_CULTIVATION,
                "mature_and_alert": MARKET_STAGE_MATURE,
                "general": MARKET_STAGE_GENERAL,
            },
        )
        self.assertEqual(
            indexed.loc["mature_and_alert", "profile_competition_alert"],
            COMPETITION_ALERT,
        )
        self.assertEqual(
            indexed.loc["gap", "profile_competition_alert"],
            NO_COMPETITION_ALERT,
        )
        self.assertEqual(
            indexed.loc["gap", "profile_demand_customer_proxy"],
            70.0,
        )
        self.assertIn("consumption_potential", thresholds.low)
        self.assertIn("competition", thresholds.high)

    def test_equal_quantile_threshold_uses_strict_low_and_high_sides(self):
        values = [0, 50, 50, 50, 100]
        frame = make_frame(
            [
                {
                    "grid_id": f"grid_{index}",
                    "has_poi_activity": True,
                    "consumption_potential": value,
                    "employment_customer_proxy": value,
                    "business_atmosphere": value,
                    "synergy": value,
                    "competition": value,
                }
                for index, value in enumerate(values)
            ]
        )

        result, thresholds = diagnose_market(
            frame,
            synergy_field="synergy",
            competition_field="competition",
        )

        self.assertEqual(thresholds.low["business_atmosphere"], 50.0)
        self.assertEqual(thresholds.high["business_atmosphere"], 50.0)
        self.assertEqual(
            result.set_index("grid_id").loc["grid_1", "profile_market_stage"],
            MARKET_STAGE_GENERAL,
        )
        self.assertEqual(
            result.set_index("grid_id").loc["grid_0", "profile_market_stage"],
            MARKET_STAGE_CULTIVATION,
        )
        self.assertEqual(
            result.set_index("grid_id").loc["grid_4", "profile_market_stage"],
            MARKET_STAGE_MATURE,
        )

    def test_inactive_rows_do_not_change_thresholds_and_are_not_diagnosed(self):
        active = make_frame(
            [
                {
                    "grid_id": "low",
                    "has_poi_activity": True,
                    "consumption_potential": 10,
                    "employment_customer_proxy": 10,
                    "business_atmosphere": 10,
                    "synergy": 10,
                    "competition": 10,
                },
                {
                    "grid_id": "high",
                    "has_poi_activity": True,
                    "consumption_potential": 90,
                    "employment_customer_proxy": 90,
                    "business_atmosphere": 90,
                    "synergy": 90,
                    "competition": 90,
                },
            ]
        )
        with_inactive = pd.concat(
            [
                active,
                make_frame(
                    [
                        {
                            "grid_id": "inactive",
                            "has_poi_activity": False,
                            "consumption_potential": 100,
                            "employment_customer_proxy": 100,
                            "business_atmosphere": 100,
                            "synergy": 100,
                            "competition": 100,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

        active_result, active_thresholds = diagnose_market(
            active,
            synergy_field="synergy",
            competition_field="competition",
        )
        result, thresholds = diagnose_market(
            with_inactive,
            synergy_field="synergy",
            competition_field="competition",
        )
        inactive = result.set_index("grid_id").loc["inactive"]

        self.assertEqual(active_thresholds, thresholds)
        self.assertEqual(
            active_result["profile_market_stage"].tolist(),
            result.iloc[:2]["profile_market_stage"].tolist(),
        )
        self.assertEqual(
            inactive["profile_market_stage"],
            INACTIVE_MARKET_STAGE,
        )
        self.assertEqual(
            inactive["profile_competition_alert"],
            INACTIVE_COMPETITION_ALERT,
        )

    def test_real_scoring_input_matches_approved_diagnostic_counts(self):
        path = Path("data/processed/grid_scoring_input.csv")
        frame = pd.read_csv(path)

        convenience, _ = diagnose_market(
            frame,
            synergy_field="convenience_synergy_score",
            competition_field="convenience_competition_pressure",
        )
        light_food, _ = diagnose_market(
            frame,
            synergy_field="light_food_synergy_score",
            competition_field="light_food_competition_pressure",
        )

        self.assertEqual(
            convenience.loc[
                convenience["has_poi_activity"],
                "profile_market_stage",
            ].value_counts().to_dict(),
            {
                MARKET_STAGE_GENERAL: 16,
                MARKET_STAGE_CULTIVATION: 12,
                MARKET_STAGE_MATURE: 12,
                MARKET_STAGE_GAP: 1,
            },
        )
        self.assertEqual(
            int(
                convenience["profile_competition_alert"]
                .eq(COMPETITION_ALERT)
                .sum()
            ),
            12,
        )
        self.assertEqual(
            light_food.loc[
                light_food["has_poi_activity"],
                "profile_market_stage",
            ].value_counts().to_dict(),
            {
                MARKET_STAGE_GENERAL: 19,
                MARKET_STAGE_MATURE: 12,
                MARKET_STAGE_CULTIVATION: 9,
                MARKET_STAGE_GAP: 1,
            },
        )
        self.assertEqual(
            int(
                light_food["profile_competition_alert"]
                .eq(COMPETITION_ALERT)
                .sum()
            ),
            13,
        )
        self.assertEqual(
            convenience.loc[
                convenience["profile_market_stage"].eq(MARKET_STAGE_GAP),
                "grid_id",
            ].tolist(),
            ["grid_520103_000046"],
        )
        self.assertEqual(
            light_food.loc[
                light_food["profile_market_stage"].eq(MARKET_STAGE_GAP),
                "grid_id",
            ].tolist(),
            ["grid_520103_000046"],
        )


if __name__ == "__main__":
    unittest.main()
