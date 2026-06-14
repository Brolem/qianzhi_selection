import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ModuleLayoutTests(unittest.TestCase):
    def test_new_feature_packages_are_importable(self):
        module_names = [
            "src.data.preprocess",
            "src.data.official_pipeline",
            "src.osm.inventory",
            "src.osm.pipeline",
            "src.selection.two_stage",
            "src.visualization.map_viz",
            "src.reporting.report_generator",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_feature_modules_keep_direct_script_entry_functions(self):
        module_entries = {
            "src.data.preprocess": "main",
            "src.data.official_pipeline": "run_official_pipeline",
            "src.osm.inventory": "main",
            "src.osm.pipeline": "main",
            "src.selection.two_stage": "main",
            "src.visualization.map_viz": "main",
            "src.reporting.report_generator": "main",
        }

        for module_name, function_name in module_entries.items():
            with self.subTest(module_name=module_name):
                module = importlib.import_module(module_name)
                self.assertTrue(callable(getattr(module, function_name)))

    def test_legacy_entry_files_are_not_left_in_src_root(self):
        root_entry_files = [
            "data_process.py",
            "official_pipeline.py",
            "osm_inventory.py",
            "osm_guizhou_pipeline.py",
            "two_stage_site_selection.py",
            "map_viz.py",
            "report_generator.py",
        ]

        for filename in root_entry_files:
            with self.subTest(filename=filename):
                self.assertFalse((Path("src") / filename).exists())

    def test_redundant_module_filenames_are_not_left_in_feature_packages(self):
        redundant_files = [
            Path("src/data/data_process.py"),
            Path("src/osm/osm_inventory.py"),
            Path("src/osm/osm_guizhou_pipeline.py"),
            Path("src/selection/two_stage_site_selection.py"),
        ]

        for path in redundant_files:
            with self.subTest(path=str(path)):
                self.assertFalse(path.exists())

    def test_official_report_uses_v2_background_scope(self):
        module = importlib.import_module("src.data.official_pipeline")
        profiles = {
            "测试文件.xlsx": {
                "shape": (1, 1),
                "duplicate_rows": 0,
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(module, "REPORTS_DIR", Path(tmp_dir)):
                path = module.write_identification_report(
                    profiles=profiles,
                    id_overlap=0,
                    macro_area_codes=[520000],
                    reference_area_codes=[520000],
                )
            content = path.read_text(encoding="utf-8")

        self.assertIn("贵州省级市场背景", content)
        self.assertIn("不参与 1km 网格评分", content)
        self.assertNotIn("当前推荐主线采用两阶段空间选址", content)


if __name__ == "__main__":
    unittest.main()
