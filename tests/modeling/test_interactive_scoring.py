import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from src.modeling.interactive_scoring import (
    EQUAL_PERCENTAGES,
    normalize_percentages,
    percentage_total,
    profile_from_percentages,
    save_custom_profile,
    score_custom_preview,
    weight_preset_percentages,
)
from src.core.profile_catalog import discover_custom_profile_specs
from src.modeling.scoring_model import WEIGHT_FIELDS


def make_scoring_input() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "grid_id": "grid_1",
                "district_name": "测试区",
                "poi_total_count": 10,
                "has_poi_activity": True,
                "traffic_accessibility": 80.0,
                "consumption_potential": 60.0,
                "employment_customer_proxy": 40.0,
                "business_atmosphere": 50.0,
                "convenience_synergy_score": 70.0,
                "light_food_synergy_score": 30.0,
                "convenience_competition_pressure": 20.0,
                "light_food_competition_pressure": 80.0,
            },
            {
                "grid_id": "grid_2",
                "district_name": "测试区",
                "poi_total_count": 0,
                "has_poi_activity": False,
                "traffic_accessibility": 0.0,
                "consumption_potential": 0.0,
                "employment_customer_proxy": 0.0,
                "business_atmosphere": 0.0,
                "convenience_synergy_score": 0.0,
                "light_food_synergy_score": 0.0,
                "convenience_competition_pressure": 0.0,
                "light_food_competition_pressure": 0.0,
            },
        ]
    )


class InteractiveScoringTests(unittest.TestCase):
    def test_presets_and_equal_percentages_are_exact(self):
        config = {
            "weights": {
                "convenience": {
                    "traffic_accessibility": 0.20,
                    "consumption_potential": 0.25,
                    "employment_customer_proxy": 0.10,
                    "synergy_score": 0.20,
                    "competition_pressure": 0.15,
                    "business_atmosphere": 0.10,
                },
                "light_food": {
                    "traffic_accessibility": 0.15,
                    "consumption_potential": 0.10,
                    "employment_customer_proxy": 0.25,
                    "synergy_score": 0.20,
                    "competition_pressure": 0.15,
                    "business_atmosphere": 0.15,
                },
            }
        }

        convenience = weight_preset_percentages("convenience", config)
        food = weight_preset_percentages("light_food", config)

        self.assertEqual(convenience["consumption_potential"], 25.0)
        self.assertEqual(food["employment_customer_proxy"], 25.0)
        self.assertEqual(percentage_total(convenience), Decimal("100.00"))
        self.assertEqual(percentage_total(food), Decimal("100.00"))
        self.assertEqual(percentage_total(EQUAL_PERCENTAGES), Decimal("100.00"))

    def test_normalization_uses_deterministic_hundredth_percent_allocation(self):
        raw = {field: 1.0 for field in WEIGHT_FIELDS}

        first = normalize_percentages(raw)
        second = normalize_percentages(raw)

        self.assertEqual(first, second)
        self.assertEqual(
            [first[field] for field in WEIGHT_FIELDS],
            [16.67, 16.67, 16.67, 16.67, 16.66, 16.66],
        )
        self.assertEqual(percentage_total(first), Decimal("100.00"))

    def test_normalization_rejects_negative_and_all_zero_values(self):
        negative = {field: 1.0 for field in WEIGHT_FIELDS}
        negative["traffic_accessibility"] = -1.0
        with self.assertRaisesRegex(ValueError, "非负"):
            normalize_percentages(negative)

        with self.assertRaisesRegex(ValueError, "不能全部为 0"):
            normalize_percentages({field: 0.0 for field in WEIGHT_FIELDS})

    def test_profile_and_preview_use_normalized_weights_without_writing(self):
        raw = {
            "traffic_accessibility": 2.0,
            "consumption_potential": 1.0,
            "employment_customer_proxy": 1.0,
            "synergy_score": 1.0,
            "competition_pressure": 1.0,
            "business_atmosphere": 0.0,
        }

        profile = profile_from_percentages(
            "preview_profile",
            "预览方案",
            "community_retail",
            raw,
            normalize=True,
        )
        scored = score_custom_preview(make_scoring_input(), profile)

        self.assertAlmostEqual(sum(profile.weights.values()), 1.0)
        self.assertEqual(profile.weights["traffic_accessibility"], 0.3333)
        self.assertEqual(int(scored["profile_rank"].notna().sum()), 1)
        self.assertEqual(float(scored.loc[1, "profile_score"]), 0.0)

    def test_save_requires_exact_input_total_and_rejects_existing_id(self):
        exact = {
            "traffic_accessibility": 20.0,
            "consumption_potential": 25.0,
            "employment_customer_proxy": 10.0,
            "synergy_score": 20.0,
            "competition_pressure": 15.0,
            "business_atmosphere": 10.0,
        }
        runner = Mock(return_value={"grid": Path("grid.csv")})
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_dir = Path(tmp_dir)
            saved = save_custom_profile(
                make_scoring_input(),
                profile_id="custom_01",
                profile_name="自定义社区业态",
                template_id="community_retail",
                percentages=exact,
                results_dir=results_dir,
                runner=runner,
            )

            self.assertEqual(saved, {"grid": Path("grid.csv")})
            profile = runner.call_args.args[1]
            self.assertAlmostEqual(sum(profile.weights.values()), 1.0)

            existing_dir = results_dir / "custom_profiles" / "custom_02"
            existing_dir.mkdir(parents=True)
            with self.assertRaisesRegex(FileExistsError, str(existing_dir).replace("\\", "\\\\")):
                save_custom_profile(
                    make_scoring_input(),
                    profile_id="custom_02",
                    profile_name="已有方案",
                    template_id="food_service",
                    percentages=exact,
                    results_dir=results_dir,
                    runner=runner,
                )

            invalid = dict(exact)
            invalid["business_atmosphere"] = 9.99
            with self.assertRaisesRegex(ValueError, "100.00"):
                save_custom_profile(
                    make_scoring_input(),
                    profile_id="custom_03",
                    profile_name="错误合计",
                    template_id="community_retail",
                    percentages=invalid,
                    results_dir=results_dir,
                    runner=runner,
                )

    def test_saved_profile_has_four_outputs_and_is_discoverable(self):
        exact = {
            "traffic_accessibility": 20.0,
            "consumption_potential": 25.0,
            "employment_customer_proxy": 10.0,
            "synergy_score": 20.0,
            "competition_pressure": 15.0,
            "business_atmosphere": 10.0,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_dir = Path(tmp_dir)
            outputs = save_custom_profile(
                make_scoring_input(),
                profile_id="saved_profile",
                profile_name="已保存方案",
                template_id="community_retail",
                percentages=exact,
                results_dir=results_dir,
            )

            self.assertEqual(
                set(outputs),
                {"grid", "district", "report", "metadata"},
            )
            self.assertTrue(all(path.exists() for path in outputs.values()))
            specs = discover_custom_profile_specs(
                results_dir / "custom_profiles"
            )
            self.assertEqual(list(specs), ["saved_profile"])


if __name__ == "__main__":
    unittest.main()
