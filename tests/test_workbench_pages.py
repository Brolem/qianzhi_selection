import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.pages.common import (
    load_required_csv,
    profile_top_rows,
)
from src.pages.data_foundation import build_data_foundation_rows
from src.pages.district_compare import load_district_comparison
from src.pages.overview import load_overview_metrics


class ProfileSpec:
    profile_id = "test_profile"
    profile_name = "测试方案"
    score_field = "profile_score"
    rank_field = "profile_rank"
    district_rank_field = "district_profile_rank"
    advantage_field = "profile_main_advantage"
    risk_field = "profile_main_risk"
    level_field = "profile_recommendation_level"
    synergy_field = "convenience_synergy_score"
    competition_pressure_field = "convenience_competition_pressure"

    def __init__(self, result_path):
        self.result_path = result_path


def write_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


class WorkbenchPageTests(unittest.TestCase):
    def test_load_required_csv_reports_exact_missing_path_and_field(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            missing = base / "missing.csv"
            with self.assertRaisesRegex(FileNotFoundError, str(missing).replace("\\", "\\\\")):
                load_required_csv(missing, ["grid_id"])

            table = write_csv(base / "table.csv", [{"grid_id": "grid_1"}])
            with self.assertRaisesRegex(KeyError, "district_name"):
                load_required_csv(table, ["grid_id", "district_name"])

    def test_load_overview_metrics_uses_real_v2_scope_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            districts = write_csv(
                base / "districts.csv",
                [{"district_name": "甲区"}, {"district_name": "乙区"}],
            )
            grids = write_csv(
                base / "grids.csv",
                [{"grid_id": "g1"}, {"grid_id": "g2"}, {"grid_id": "g3"}],
            )
            poi_counts = write_csv(
                base / "poi.csv",
                [{"grid_id": "g1"}, {"grid_id": "g2"}],
            )
            scores = write_csv(
                base / "scores.csv",
                [
                    {"grid_id": "g1", "has_poi_activity": True},
                    {"grid_id": "g2", "has_poi_activity": False},
                ],
            )

            result = load_overview_metrics(
                districts_path=districts,
                grids_path=grids,
                poi_counts_path=poi_counts,
                scores_path=scores,
                profile_specs={"默认": object(), "自定义": object()},
                poi_categories={
                    "convenience_store": "便利店",
                    "restaurant": "餐饮",
                },
            )

            self.assertEqual(
                result,
                {
                    "district_count": 2,
                    "spatial_grid_count": 3,
                    "poi_sample_grid_count": 2,
                    "poi_category_count": 2,
                    "active_grid_count": 1,
                    "profile_count": 2,
                },
            )

    def test_build_data_foundation_rows_uses_exact_files_and_roles(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            districts = write_csv(
                base / "target_districts.csv",
                [
                    {
                        "district_name": "甲区",
                        "adcode": "520101",
                        "data_source": "amap_api",
                    }
                ],
            )
            poi_counts = write_csv(
                base / "grid_poi_counts.csv",
                [{"grid_id": "g1", "district_name": "甲区"}],
            )
            macro = write_csv(
                base / "macro_clean.csv",
                [
                    {
                        "area_code": "520000",
                        "index_name": "测试指标",
                        "value": 1,
                    }
                ],
            )
            employment = write_csv(
                base / "employment_clean.csv",
                [{"region_id": "520000", "region_name": "贵州省"}],
            )

            rows = build_data_foundation_rows(
                districts_path=districts,
                poi_counts_path=poi_counts,
                macro_path=macro,
                employment_path=employment,
            )

            self.assertEqual([row["record_count"] for row in rows], [1, 1, 1, 1])
            self.assertEqual(rows[0]["data_role"], "区县边界与空间约束")
            self.assertEqual(rows[1]["geographic_scope"], "贵阳市三个目标区县的 60 个样本网格")
            self.assertEqual(rows[2]["geographic_scope"], "贵州省级背景")
            self.assertEqual(rows[3]["geographic_scope"], "贵州省级背景")

    def test_profile_top_rows_filters_activity_district_and_rank(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_csv(
                Path(tmp_dir) / "scores.csv",
                [
                    {
                        "grid_id": "g3",
                        "district_name": "乙区",
                        "has_poi_activity": True,
                        "profile_score": 70,
                        "profile_rank": 3,
                    },
                    {
                        "grid_id": "g1",
                        "district_name": "甲区",
                        "has_poi_activity": True,
                        "profile_score": 90,
                        "profile_rank": 1,
                    },
                    {
                        "grid_id": "g2",
                        "district_name": "甲区",
                        "has_poi_activity": False,
                        "profile_score": 0,
                        "profile_rank": None,
                    },
                ],
            )
            spec = ProfileSpec(result_path)

            all_rows = profile_top_rows(spec, limit=5)
            district_rows = profile_top_rows(spec, district_name="甲区", limit=10)

            self.assertEqual(all_rows["grid_id"].tolist(), ["g1", "g3"])
            self.assertEqual(district_rows["grid_id"].tolist(), ["g1"])

    def test_load_district_comparison_requires_step8_summary_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_csv(
                Path(tmp_dir) / "district_summary.csv",
                [
                    {
                        "district_name": "甲区",
                        "grid_count": 20,
                        "active_grid_count": 12,
                        "poi_total_count": 100,
                        "avg_convenience_score": 50,
                        "top_convenience_grid_id": "g1",
                        "avg_light_food_score": 48,
                        "top_light_food_grid_id": "g2",
                    }
                ],
            )

            result = load_district_comparison(path)

            self.assertEqual(result["district_name"].tolist(), ["甲区"])
            self.assertEqual(result["active_grid_count"].tolist(), [12])


if __name__ == "__main__":
    unittest.main()
