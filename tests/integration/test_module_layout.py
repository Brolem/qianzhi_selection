import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ModuleLayoutTests(unittest.TestCase):
    def test_new_feature_packages_are_importable(self):
        module_names = [
            "src.pipeline.official.preprocess",
            "src.pipeline.official.official_pipeline",
            "src.legacy.v1.osm.inventory",
            "src.legacy.v1.osm.pipeline",
            "src.legacy.v1.selection.two_stage",
            "src.presentation.map_viz",
            "src.presentation.report_generator",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_feature_modules_keep_direct_script_entry_functions(self):
        module_entries = {
            "src.pipeline.official.preprocess": "main",
            "src.pipeline.official.official_pipeline": "run_official_pipeline",
            "src.legacy.v1.osm.inventory": "main",
            "src.legacy.v1.osm.pipeline": "main",
            "src.legacy.v1.selection.two_stage": "main",
            "src.presentation.map_viz": "main",
            "src.presentation.report_generator": "main",
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
            Path("src/pipeline/official/data_process.py"),
            Path("src/legacy/v1/osm/osm_inventory.py"),
            Path("src/legacy/v1/osm/osm_guizhou_pipeline.py"),
            Path("src/legacy/v1/selection/two_stage_site_selection.py"),
        ]

        for path in redundant_files:
            with self.subTest(path=str(path)):
                self.assertFalse(path.exists())

    def test_official_report_uses_v2_background_scope(self):
        module = importlib.import_module("src.pipeline.official.official_pipeline")
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
