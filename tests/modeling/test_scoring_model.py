import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.modeling import scoring_model


WEIGHT_FIELDS = scoring_model.WEIGHT_FIELDS


def make_weights(**overrides):
    values = {
        "traffic_accessibility": 1.0,
        "consumption_potential": 0.0,
        "employment_customer_proxy": 0.0,
        "synergy_score": 0.0,
        "competition_pressure": 0.0,
        "business_atmosphere": 0.0,
    }
    values.update(overrides)
    return values


def make_profile(
    profile_id="test_profile",
    profile_name="测试方案",
    template_id="community_retail",
    weights=None,
):
    return scoring_model.ScoringProfile(
        profile_id=profile_id,
        profile_name=profile_name,
        template_id=template_id,
        weights=weights or make_weights(),
    )


def make_scoring_input(rows=4, inactive_indices=None):
    inactive = set(inactive_indices or [])
    data = []
    for index in range(rows):
        active = index not in inactive
        value = min(float(rows - index) * 10.0, 100.0) if active else 0.0
        data.append(
            {
                "grid_id": f"grid_520101_{index + 1:06d}",
                "district_name": "测试区",
                "adcode": "520101",
                "centroid_lon": 106.6 + index * 0.01,
                "centroid_lat": 26.5 + index * 0.01,
                "area_km2": 1.0,
                "data_source": "amap_boundary",
                "poi_total_count": int(value),
                "poi_category_coverage": 1 if active else 0,
                "has_poi_activity": active,
                "traffic_accessibility": value,
                "consumption_potential": value / 2,
                "employment_customer_proxy": value / 4,
                "business_atmosphere": value / 5,
                "convenience_synergy_score": value / 2,
                "light_food_synergy_score": value / 3,
                "convenience_competition_pressure": min(value / 2, 100),
                "light_food_competition_pressure": min(value / 3, 100),
            }
        )
    return pd.DataFrame(data)


class ScoringModelTests(unittest.TestCase):
    def test_profile_validation_rejects_invalid_identifiers_templates_and_weights(self):
        templates = scoring_model.DEFAULT_TEMPLATES
        invalid_cases = [
            (make_profile(profile_id="Bad-ID"), "profile_id"),
            (make_profile(profile_name=" "), "profile_name"),
            (make_profile(template_id="unknown"), "template_id"),
            (make_profile(weights={"traffic_accessibility": 1.0}), "权重字段"),
            (
                make_profile(
                    weights=make_weights(
                        traffic_accessibility=1.1,
                        consumption_potential=-0.1,
                    )
                ),
                "0-1",
            ),
            (
                make_profile(
                    weights=make_weights(
                        traffic_accessibility=0.8,
                        consumption_potential=0.1,
                    )
                ),
                "总和必须为 1",
            ),
        ]
        for profile, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    scoring_model.validate_profile(profile, templates)

    def test_score_profile_uses_template_fields_and_reverses_competition(self):
        frame = make_scoring_input(rows=2)
        frame.loc[0, "convenience_competition_pressure"] = 20.0
        frame.loc[0, "light_food_competition_pressure"] = 70.0
        competition_only = make_weights(
            traffic_accessibility=0.0,
            competition_pressure=1.0,
        )

        retail = scoring_model.score_profile(
            frame,
            make_profile(weights=competition_only),
        )
        food = scoring_model.score_profile(
            frame,
            make_profile(
                profile_id="food",
                template_id="food_service",
                weights=competition_only,
            ),
        )

        self.assertEqual(retail.loc[0, "profile_competition_score"], 80.0)
        self.assertEqual(retail.loc[0, "profile_score"], 80.0)
        self.assertEqual(food.loc[0, "profile_competition_score"], 30.0)
        self.assertEqual(food.loc[0, "profile_score"], 30.0)

    def test_score_profile_uses_exact_weighted_formula(self):
        frame = make_scoring_input(rows=1)
        frame.loc[0, [
            "traffic_accessibility",
            "consumption_potential",
            "employment_customer_proxy",
            "convenience_synergy_score",
            "convenience_competition_pressure",
            "business_atmosphere",
        ]] = [10, 20, 30, 40, 50, 60]
        weights = {
            "traffic_accessibility": 0.20,
            "consumption_potential": 0.25,
            "employment_customer_proxy": 0.10,
            "synergy_score": 0.20,
            "competition_pressure": 0.15,
            "business_atmosphere": 0.10,
        }

        result = scoring_model.score_profile(
            frame,
            make_profile(weights=weights),
        )

        self.assertAlmostEqual(result.loc[0, "profile_score"], 31.5)

    def test_score_profile_adds_diagnostics_without_changing_weighted_score(self):
        frame = make_scoring_input(rows=6)
        traffic_only = make_profile(
            profile_id="traffic_only",
            weights=make_weights(),
        )
        consumption_only = make_profile(
            profile_id="consumption_only",
            weights=make_weights(
                traffic_accessibility=0.0,
                consumption_potential=1.0,
            ),
        )

        traffic = scoring_model.score_profile(frame, traffic_only)
        consumption = scoring_model.score_profile(frame, consumption_only)

        for field in [
            "profile_demand_customer_proxy",
            "profile_market_stage",
            "profile_competition_alert",
            "profile_diagnosis_summary",
        ]:
            self.assertIn(field, traffic)
        self.assertEqual(
            traffic["profile_market_stage"].tolist(),
            consumption["profile_market_stage"].tolist(),
        )
        self.assertEqual(
            traffic["profile_competition_alert"].tolist(),
            consumption["profile_competition_alert"].tolist(),
        )
        self.assertEqual(
            traffic["profile_score"].tolist(),
            frame["traffic_accessibility"].astype(float).tolist(),
        )

    def test_ranking_is_deterministic_and_inactive_grids_have_no_rank(self):
        frame = make_scoring_input(rows=4, inactive_indices=[3])
        frame.loc[0:2, "traffic_accessibility"] = 50.0
        frame.loc[0:2, "poi_total_count"] = [10, 20, 20]

        result = scoring_model.score_profile(frame, make_profile())

        ranked = result[result["profile_rank"].notna()].sort_values("profile_rank")
        self.assertEqual(
            ranked["grid_id"].tolist(),
            [
                "grid_520101_000002",
                "grid_520101_000003",
                "grid_520101_000001",
            ],
        )
        inactive = result[result["has_poi_activity"].eq(False)].iloc[0]
        self.assertEqual(float(inactive["profile_score"]), 0.0)
        self.assertTrue(pd.isna(inactive["profile_rank"]))
        self.assertTrue(pd.isna(inactive["district_profile_rank"]))

    def test_level_distribution_for_forty_one_active_and_nineteen_inactive_grids(self):
        frame = make_scoring_input(rows=60, inactive_indices=range(41, 60))

        result = scoring_model.score_profile(frame, make_profile())
        active_levels = result[result["has_poi_activity"]]["profile_recommendation_level"]
        inactive_levels = result[~result["has_poi_activity"]]["profile_recommendation_level"]

        self.assertEqual(
            active_levels.value_counts().to_dict(),
            {"谨慎推荐": 16, "暂不推荐": 16, "推荐": 9},
        )
        self.assertEqual(inactive_levels.value_counts().to_dict(), {"暂不推荐": 19})

    def test_advantage_and_risk_follow_metric_direction(self):
        frame = make_scoring_input(rows=1)
        frame.loc[0, [
            "traffic_accessibility",
            "consumption_potential",
            "employment_customer_proxy",
            "convenience_synergy_score",
            "convenience_competition_pressure",
            "business_atmosphere",
        ]] = [90, 60, 70, 80, 95, 85]

        result = scoring_model.score_profile(frame, make_profile())

        self.assertEqual(result.loc[0, "profile_main_advantage"], "交通可达性")
        self.assertEqual(result.loc[0, "profile_main_risk"], "竞争压力较高")

        inactive = make_scoring_input(rows=1, inactive_indices=[0])
        inactive_result = scoring_model.score_profile(inactive, make_profile())
        self.assertEqual(
            inactive_result.loc[0, "profile_main_advantage"],
            "未检测到POI活动",
        )
        self.assertEqual(
            inactive_result.loc[0, "profile_main_risk"],
            "缺少可用于推荐的POI活动",
        )

    def test_default_results_use_two_profiles_without_generic_explanation_fields(self):
        frame = make_scoring_input(rows=3)
        profiles = {
            "convenience": make_profile(
                profile_id="convenience",
                profile_name="社区便利店",
            ),
            "light_food": make_profile(
                profile_id="light_food",
                profile_name="轻餐饮",
                template_id="food_service",
            ),
        }

        result = scoring_model.build_default_grid_result(frame, profiles)

        self.assertIn("convenience_score", result)
        self.assertIn("light_food_score", result)
        self.assertIn("convenience_main_advantage", result)
        self.assertIn("light_food_main_risk", result)
        self.assertIn("convenience_market_stage", result)
        self.assertIn("light_food_competition_alert", result)
        self.assertIn("convenience_diagnosis_summary", result)
        self.assertNotIn("main_advantage", result)
        self.assertNotIn("main_risk", result)

    def test_district_summary_uses_active_grids_only_for_scores(self):
        frame = make_scoring_input(rows=3, inactive_indices=[2])
        scored = scoring_model.score_profile(frame, make_profile())

        summary = scoring_model.build_profile_district_summary(scored)

        self.assertEqual(int(summary.loc[0, "grid_count"]), 3)
        self.assertEqual(int(summary.loc[0, "active_grid_count"]), 2)
        self.assertAlmostEqual(
            summary.loc[0, "avg_profile_score"],
            scored.loc[scored["has_poi_activity"], "profile_score"].mean(),
        )
        self.assertEqual(
            summary.loc[0, "top_profile_grid_id"],
            scored.sort_values("profile_rank").iloc[0]["grid_id"],
        )
        stage_total = sum(
            int(summary.loc[0, field])
            for field in [
                "market_gap_grid_count",
                "cultivation_grid_count",
                "mature_grid_count",
                "general_observation_grid_count",
            ]
        )
        self.assertEqual(stage_total, int(summary.loc[0, "active_grid_count"]))
        self.assertEqual(
            int(summary.loc[0, "over_competition_alert_count"]),
            int(
                scored["profile_competition_alert"]
                .eq("过度竞争预警")
                .sum()
            ),
        )

    def test_custom_cli_requires_complete_parameter_set(self):
        parser = scoring_model.build_parser()
        incomplete = parser.parse_args(["--profile-id", "custom_01"])
        with self.assertRaisesRegex(ValueError, "自定义评分参数必须全部提供"):
            scoring_model.profile_from_args(incomplete)

        complete = parser.parse_args(
            [
                "--profile-id", "custom_01",
                "--profile-name", "自定义社区业态",
                "--template", "community_retail",
                "--traffic-weight", "0.20",
                "--consumption-weight", "0.25",
                "--employment-weight", "0.10",
                "--synergy-weight", "0.20",
                "--competition-weight", "0.15",
                "--atmosphere-weight", "0.10",
            ]
        )
        profile = scoring_model.profile_from_args(complete)
        self.assertEqual(profile.profile_id, "custom_01")
        self.assertEqual(profile.template_id, "community_retail")
        self.assertAlmostEqual(sum(profile.weights.values()), 1.0)

    def test_four_output_failure_restores_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            paths = {
                "grid": base / "grid.csv",
                "district": base / "district.csv",
                "report": base / "report.md",
                "metadata": base / "profile_metadata.json",
            }
            for key, path in paths.items():
                path.write_text(f"existing {key}", encoding="utf-8")
            real_replace = os.replace
            call_count = 0

            def fail_fourth_replace(source, target):
                nonlocal call_count
                call_count += 1
                if call_count == 4:
                    raise OSError("simulated metadata replace failure")
                return real_replace(source, target)

            with patch(
                "src.modeling.scoring_model.os.replace",
                side_effect=fail_fourth_replace,
            ):
                with self.assertRaisesRegex(OSError, "simulated metadata replace failure"):
                    scoring_model.write_profile_outputs_atomically(
                        grid_result=make_scoring_input(rows=1),
                        district_summary=pd.DataFrame([{"district_name": "测试区"}]),
                        report="new report",
                        metadata={"schema_version": 1, "profiles": []},
                        grid_path=paths["grid"],
                        district_path=paths["district"],
                        report_path=paths["report"],
                        metadata_path=paths["metadata"],
                    )

            for key, path in paths.items():
                self.assertEqual(path.read_text(encoding="utf-8"), f"existing {key}")

    def test_custom_profile_outputs_are_isolated_by_profile_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_dir = Path(tmp_dir)
            frame = make_scoring_input(rows=3)
            first = make_profile(profile_id="custom_01")
            second = make_profile(profile_id="custom_02")

            first_paths = scoring_model.run_custom_profile(frame, first, results_dir)
            second_paths = scoring_model.run_custom_profile(frame, second, results_dir)

            self.assertEqual(first_paths["grid"].parent.name, "custom_01")
            self.assertEqual(second_paths["grid"].parent.name, "custom_02")
            self.assertTrue(first_paths["grid"].exists())
            self.assertTrue(second_paths["grid"].exists())
            self.assertTrue(first_paths["metadata"].exists())
            first_result = pd.read_csv(first_paths["grid"])
            self.assertIn("profile_score", first_result)
            self.assertEqual(first_result["profile_id"].unique().tolist(), ["custom_01"])
            metadata = json.loads(
                first_paths["metadata"].read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["profiles"][0]["profile_id"], "custom_01")
            self.assertEqual(metadata["profiles"][0]["weights"], first.weights)

    def test_default_outputs_include_two_profile_metadata_records(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_dir = Path(tmp_dir)
            frame = make_scoring_input(rows=3)
            profiles = {
                "convenience": make_profile(
                    profile_id="convenience",
                    profile_name="社区便利店",
                ),
                "light_food": make_profile(
                    profile_id="light_food",
                    profile_name="轻餐饮",
                    template_id="food_service",
                ),
            }

            paths = scoring_model.run_default_scoring(
                frame,
                profiles,
                scoring_model.DEFAULT_TEMPLATES,
                results_dir,
            )

            metadata = json.loads(
                paths["metadata"].read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(
                [item["profile_id"] for item in metadata["profiles"]],
                ["convenience", "light_food"],
            )
            report = paths["report"].read_text(encoding="utf-8")
            self.assertIn("## 区域市场诊断", report)
            self.assertIn("市场空白型", report)
            self.assertIn("过度竞争预警", report)
            self.assertIn("需求客群代理不是真实客流", report)


if __name__ == "__main__":
    unittest.main()
