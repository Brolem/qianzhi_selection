import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src import feature_engineering


def make_counts(rows=2):
    data = []
    for index in range(rows):
        row = {
            "grid_id": f"grid_520101_{index + 1:06d}",
            "district_name": "测试区",
        }
        row.update({field: 0 for field in feature_engineering.COUNT_FIELDS})
        data.append(row)
    return pd.DataFrame(data)


def make_grids(rows=2):
    return pd.DataFrame(
        [
            {
                "grid_id": f"grid_520101_{index + 1:06d}",
                "district_name": "测试区",
                "adcode": "520101",
                "centroid_lon": 106.6 + index * 0.01,
                "centroid_lat": 26.5 + index * 0.01,
                "area_km2": 1.0,
                "geometry_wkt": "",
                "data_source": "amap_boundary",
            }
            for index in range(rows)
        ]
    )


class FeatureEngineeringTests(unittest.TestCase):
    def test_log_minmax_scales_to_zero_and_one_hundred(self):
        result = feature_engineering.log_minmax(pd.Series([0, 3]))
        constant = feature_engineering.log_minmax(pd.Series([5, 5]))

        self.assertEqual(result.tolist(), [0.0, 100.0])
        self.assertEqual(constant.tolist(), [0.0, 0.0])
        self.assertAlmostEqual(math.log1p(3), math.log(4))

    def test_build_scoring_input_uses_exact_equal_weight_metrics(self):
        counts = make_counts()
        active_fields = {
            field
            for fields in feature_engineering.METRIC_COMPONENTS.values()
            for field in fields
        }
        counts.loc[0, list(active_fields)] = 1

        result = feature_engineering.build_grid_scoring_input(counts, make_grids())

        self.assertEqual(result.columns.tolist(), feature_engineering.OUTPUT_FIELDS)
        self.assertEqual(result.loc[0, feature_engineering.METRIC_FIELDS].tolist(), [100.0] * 8)
        self.assertEqual(result.loc[1, feature_engineering.METRIC_FIELDS].tolist(), [0.0] * 8)
        self.assertEqual(int(result.loc[0, "poi_total_count"]), len(active_fields))
        self.assertEqual(int(result.loc[0, "poi_category_coverage"]), len(active_fields))
        self.assertTrue(bool(result.loc[0, "has_poi_activity"]))
        self.assertFalse(bool(result.loc[1, "has_poi_activity"]))

    def test_missing_counts_are_zero_and_all_zero_grid_is_preserved(self):
        counts = make_counts(rows=1)
        counts.loc[0, "parking_count"] = None

        result = feature_engineering.build_grid_scoring_input(counts, make_grids(rows=1))

        self.assertEqual(len(result), 1)
        self.assertEqual(int(result.loc[0, "parking_count"]), 0)
        self.assertEqual(int(result.loc[0, "poi_total_count"]), 0)
        self.assertEqual(int(result.loc[0, "poi_category_coverage"]), 0)
        self.assertFalse(bool(result.loc[0, "has_poi_activity"]))
        self.assertEqual(result.loc[0, feature_engineering.METRIC_FIELDS].tolist(), [0.0] * 8)

    def test_invalid_count_values_raise_clear_errors(self):
        for value, message in [(-1, "不能为负数"), ("不是数字", "必须为数字")]:
            with self.subTest(value=value):
                counts = make_counts()
                if isinstance(value, str):
                    counts["parking_count"] = counts["parking_count"].astype(object)
                counts.loc[0, "parking_count"] = value
                with self.assertRaisesRegex(ValueError, f"parking_count.*{message}"):
                    feature_engineering.build_grid_scoring_input(counts, make_grids())

    def test_duplicate_and_unmatched_grids_raise_clear_errors(self):
        duplicate_counts = pd.concat([make_counts(), make_counts().iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "POI 统计存在重复网格"):
            feature_engineering.build_grid_scoring_input(duplicate_counts, make_grids())

        duplicate_grids = pd.concat([make_grids(), make_grids().iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "评价网格存在重复网格"):
            feature_engineering.build_grid_scoring_input(make_counts(), duplicate_grids)

        missing_grid = make_grids().iloc[[0]].copy()
        with self.assertRaisesRegex(ValueError, "缺少空间信息.*grid_520101_000002"):
            feature_engineering.build_grid_scoring_input(make_counts(), missing_grid)

        wrong_district = make_grids()
        wrong_district.loc[0, "district_name"] = "其他区"
        with self.assertRaisesRegex(ValueError, "区县不一致.*grid_520101_000001"):
            feature_engineering.build_grid_scoring_input(make_counts(), wrong_district)

    def test_validate_output_scope_requires_exact_district_distribution(self):
        counts = make_counts()
        result = feature_engineering.build_grid_scoring_input(counts, make_grids())

        feature_engineering.validate_output_scope(
            result,
            expected_districts=["测试区"],
            grids_per_district=2,
        )
        with self.assertRaisesRegex(ValueError, "应为 3 行，实际为 2 行"):
            feature_engineering.validate_output_scope(
                result,
                expected_districts=["测试区"],
                grids_per_district=3,
            )

    def test_run_writes_exact_output_and_report_without_requiring_official_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            counts_path = base / "grid_poi_counts.csv"
            grids_path = base / "candidate_grids.csv"
            output_path = base / "processed" / "grid_scoring_input.csv"
            report_path = base / "results" / "feature_engineering_report.md"
            make_counts().to_csv(counts_path, index=False, encoding="utf-8-sig")
            make_grids().to_csv(grids_path, index=False, encoding="utf-8-sig")

            outputs = feature_engineering.run_feature_engineering(
                counts_path=counts_path,
                grids_path=grids_path,
                output_path=output_path,
                report_path=report_path,
                expected_districts=["测试区"],
                grids_per_district=2,
                total_spatial_grid_count=790,
            )
            written = pd.read_csv(outputs["scoring"])
            report = outputs["report"].read_text(encoding="utf-8")

        self.assertEqual(written.columns.tolist(), feature_engineering.OUTPUT_FIELDS)
        self.assertIn("log1p", report)
        self.assertIn("60 个样本网格", report)
        self.assertIn("790 个空间网格", report)
        self.assertIn("data/processed/official/", report)
        self.assertIn("同一查询口径下的相对评价", report)

    def test_failure_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            counts_path = base / "grid_poi_counts.csv"
            grids_path = base / "candidate_grids.csv"
            output_path = base / "processed" / "grid_scoring_input.csv"
            report_path = base / "results" / "feature_engineering_report.md"
            output_path.parent.mkdir(parents=True)
            report_path.parent.mkdir(parents=True)
            output_path.write_text("existing scoring", encoding="utf-8")
            report_path.write_text("existing report", encoding="utf-8")
            invalid_counts = make_counts()
            invalid_counts.loc[0, "parking_count"] = -1
            invalid_counts.to_csv(counts_path, index=False, encoding="utf-8-sig")
            make_grids().to_csv(grids_path, index=False, encoding="utf-8-sig")

            with self.assertRaisesRegex(ValueError, "parking_count.*不能为负数"):
                feature_engineering.run_feature_engineering(
                    counts_path=counts_path,
                    grids_path=grids_path,
                    output_path=output_path,
                    report_path=report_path,
                    expected_districts=["测试区"],
                    grids_per_district=2,
                    total_spatial_grid_count=790,
                )

            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing scoring")
            self.assertEqual(report_path.read_text(encoding="utf-8"), "existing report")

    def test_second_replace_failure_restores_both_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            output_path = base / "processed" / "grid_scoring_input.csv"
            report_path = base / "results" / "feature_engineering_report.md"
            output_path.parent.mkdir(parents=True)
            report_path.parent.mkdir(parents=True)
            output_path.write_text("existing scoring", encoding="utf-8")
            report_path.write_text("existing report", encoding="utf-8")
            scoring = feature_engineering.build_grid_scoring_input(
                make_counts(),
                make_grids(),
            )
            real_replace = os.replace
            call_count = 0

            def fail_second_replace(source, target):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("simulated report replace failure")
                return real_replace(source, target)

            with patch(
                "src.feature_engineering.os.replace",
                side_effect=fail_second_replace,
            ):
                with self.assertRaisesRegex(OSError, "simulated report replace failure"):
                    feature_engineering.write_outputs_atomically(
                        scoring,
                        "new report",
                        output_path,
                        report_path,
                    )

            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing scoring")
            self.assertEqual(report_path.read_text(encoding="utf-8"), "existing report")


if __name__ == "__main__":
    unittest.main()
