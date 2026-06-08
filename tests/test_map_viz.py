import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.map_viz import (
    build_grid_map,
    build_region_map,
    load_grid_result,
    load_region_result,
    write_default_maps,
)


class MapVizTests(unittest.TestCase):
    def test_load_grid_result_requires_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.csv"

            with self.assertRaises(FileNotFoundError):
                load_grid_result(missing_path)

    def test_build_grid_map_uses_business_score_and_tooltip_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            grid_path = Path(tmp_dir) / "grid_stage_score_result.csv"
            pd.DataFrame(
                [
                    {
                        "grid_id": "grid_8316193_000001",
                        "region_id": "grid_8316193_000001",
                        "grid_region_name": "测试区域",
                        "centroid_lon": 106.7,
                        "centroid_lat": 26.6,
                        "convenience_score": 0.81,
                        "light_food_score": 0.62,
                        "main_advantage": "交通可达性",
                        "main_risk": "竞争压力较低",
                    }
                ]
            ).to_csv(grid_path, index=False, encoding="utf-8-sig")

            result_map = build_grid_map("convenience", grid_path=grid_path)
            html = result_map.get_root().render()

            self.assertIn("grid_8316193_000001", html)
            self.assertIn("交通可达性", html)
            self.assertIn("竞争压力较低", html)
            self.assertIn("0.810", html)

    def test_write_default_maps_exports_two_html_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            grid_path = base / "grid_stage_score_result.csv"
            region_path = base / "region_stage_score_result.csv"
            output_dir = base / "figures"
            pd.DataFrame(
                [
                    {
                        "grid_id": "grid_1",
                        "region_id": "grid_1",
                        "grid_region_name": "测试区域",
                        "centroid_lon": 106.7,
                        "centroid_lat": 26.6,
                        "convenience_score": 0.9,
                        "light_food_score": 0.8,
                        "main_advantage": "消费潜力",
                        "main_risk": "区域发展基础",
                    }
                ]
            ).to_csv(grid_path, index=False, encoding="utf-8-sig")
            pd.DataFrame(
                [
                    {
                        "region_id": "8316193",
                        "region_name": "测试区域",
                        "convenience_score": 0.7,
                        "light_food_score": 0.6,
                        "main_advantage": "消费潜力",
                        "main_risk": "区域发展基础",
                    }
                ]
            ).to_csv(region_path, index=False, encoding="utf-8-sig")

            outputs = write_default_maps(grid_path=grid_path, region_path=region_path, output_dir=output_dir)

            self.assertEqual(
                {path.name for path in outputs},
                {"convenience_grid_map.html", "light_food_grid_map.html"},
            )
            for path in outputs:
                self.assertTrue(path.exists())
                self.assertIn("grid_1", path.read_text(encoding="utf-8"))

    def test_build_region_map_loads_region_result_without_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            region_path = Path(tmp_dir) / "region_stage_score_result.csv"
            pd.DataFrame(
                [
                    {
                        "region_id": "8316193",
                        "region_name": "测试区域",
                        "convenience_score": 0.7,
                        "light_food_score": 0.6,
                        "main_advantage": "消费潜力",
                        "main_risk": "区域发展基础",
                    }
                ]
            ).to_csv(region_path, index=False, encoding="utf-8-sig")

            region_df = load_region_result(region_path)
            result_map = build_region_map("light_food", region_path=region_path)
            html = result_map.get_root().render()

            self.assertEqual(region_df["region_id"].astype(str).tolist(), ["8316193"])
            self.assertIn("8316193", html)
            self.assertIn("0.600", html)


if __name__ == "__main__":
    unittest.main()
