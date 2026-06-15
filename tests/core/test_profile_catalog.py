import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.core import profile_catalog


WEIGHTS = {
    "traffic_accessibility": 0.20,
    "consumption_potential": 0.25,
    "employment_customer_proxy": 0.10,
    "synergy_score": 0.20,
    "competition_pressure": 0.15,
    "business_atmosphere": 0.10,
}


def write_metadata(path: Path, profiles: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": profiles,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def write_custom_result(path: Path, profile_id: str = "custom_01") -> Path:
    pd.DataFrame(
        [
            {
                "grid_id": "grid_520101_000001",
                "district_name": "测试区",
                "centroid_lon": 106.7,
                "centroid_lat": 26.6,
                "area_km2": 1.0,
                "poi_total_count": 12,
                "poi_category_coverage": 5,
                "has_poi_activity": True,
                "traffic_accessibility": 80.0,
                "consumption_potential": 70.0,
                "employment_customer_proxy": 60.0,
                "business_atmosphere": 50.0,
                "convenience_synergy_score": 65.0,
                "convenience_competition_pressure": 30.0,
                "profile_id": profile_id,
                "profile_name": "自定义社区业态",
                "template_id": "community_retail",
                "profile_competition_score": 70.0,
                "profile_score": 68.0,
                "profile_rank": 1,
                "district_profile_rank": 1,
                "profile_main_advantage": "交通可达性",
                "profile_main_risk": "商业氛围不足",
                "profile_recommendation_level": "推荐",
                "profile_demand_customer_proxy": 65.0,
                "profile_market_stage": "一般观察型",
                "profile_competition_alert": "未触发过度竞争预警",
                "profile_diagnosis_summary": "一般观察型；未触发过度竞争预警",
            }
        ]
    ).to_csv(path, index=False, encoding="utf-8-sig")
    return path


class ProfileCatalogTests(unittest.TestCase):
    def test_default_specs_use_exact_step8_fields_and_metadata_weights(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            metadata_path = write_metadata(
                base / "profile_metadata.json",
                [
                    {
                        "profile_id": "convenience",
                        "profile_name": "社区便利店",
                        "template_id": "community_retail",
                        "weights": WEIGHTS,
                    },
                    {
                        "profile_id": "light_food",
                        "profile_name": "轻餐饮",
                        "template_id": "food_service",
                        "weights": WEIGHTS,
                    },
                ],
            )

            specs = profile_catalog.default_profile_specs(
                result_path=base / "grid_stage_score_result.csv",
                metadata_path=metadata_path,
                figures_dir=base / "figures",
            )

            convenience = specs["convenience"]
            self.assertEqual(convenience.score_field, "convenience_score")
            self.assertEqual(
                convenience.competition_pressure_field,
                "convenience_competition_pressure",
            )
            self.assertEqual(
                convenience.synergy_field,
                "convenience_synergy_score",
            )
            self.assertEqual(
                convenience.market_stage_field,
                "convenience_market_stage",
            )
            self.assertEqual(
                convenience.competition_alert_field,
                "convenience_competition_alert",
            )
            self.assertEqual(convenience.weights, WEIGHTS)
            self.assertEqual(
                specs["light_food"].rank_field,
                "light_food_rank",
            )

    def test_custom_spec_requires_matching_directory_metadata_and_result(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            profile_dir = base / "custom_01"
            profile_dir.mkdir()
            write_custom_result(profile_dir / "grid_score_result.csv")
            write_metadata(
                profile_dir / "profile_metadata.json",
                [
                    {
                        "profile_id": "custom_01",
                        "profile_name": "自定义社区业态",
                        "template_id": "community_retail",
                        "weights": WEIGHTS,
                    }
                ],
            )

            specs = profile_catalog.discover_custom_profile_specs(base)

            spec = specs["custom_01"]
            self.assertEqual(spec.score_field, "profile_score")
            self.assertEqual(spec.rank_field, "profile_rank")
            self.assertEqual(
                spec.competition_pressure_field,
                "convenience_competition_pressure",
            )
            self.assertEqual(
                spec.diagnosis_summary_field,
                "profile_diagnosis_summary",
            )
            self.assertEqual(spec.weights, WEIGHTS)

            metadata = json.loads(
                (profile_dir / "profile_metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            metadata["profiles"][0]["profile_id"] = "other_id"
            (profile_dir / "profile_metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "custom_01"):
                profile_catalog.discover_custom_profile_specs(base)

    def test_metadata_rejects_missing_weight_and_unknown_template(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            incomplete = dict(WEIGHTS)
            incomplete.pop("business_atmosphere")
            metadata_path = write_metadata(
                base / "profile_metadata.json",
                [
                    {
                        "profile_id": "convenience",
                        "profile_name": "社区便利店",
                        "template_id": "unknown",
                        "weights": incomplete,
                    }
                ],
            )

            with self.assertRaises(ValueError):
                profile_catalog.load_profile_metadata(metadata_path)


if __name__ == "__main__":
    unittest.main()
