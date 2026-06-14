import ast
import importlib
from pathlib import Path
import unittest

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StructureBoundaryTests(unittest.TestCase):
    def test_current_modules_use_responsibility_packages(self):
        module_names = [
            "src.core.config",
            "src.core.profile_catalog",
            "src.pipeline.amap_client",
            "src.pipeline.district_builder",
            "src.pipeline.grid_builder",
            "src.pipeline.poi_fetcher",
            "src.pipeline.official.preprocess",
            "src.pipeline.official.official_pipeline",
            "src.modeling.feature_engineering",
            "src.modeling.interactive_scoring",
            "src.modeling.scoring_model",
            "src.presentation.map_viz",
            "src.presentation.report_generator",
            "src.web.pages.overview",
            "src.web.ui.workbench",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_current_source_does_not_import_legacy_package(self):
        current_roots = [
            PROJECT_ROOT / "src" / "app.py",
            PROJECT_ROOT / "src" / "core",
            PROJECT_ROOT / "src" / "pipeline",
            PROJECT_ROOT / "src" / "modeling",
            PROJECT_ROOT / "src" / "presentation",
            PROJECT_ROOT / "src" / "web",
        ]

        for root in current_roots:
            paths = [root] if root.is_file() else root.rglob("*.py")
            for path in paths:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                imported_modules = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_modules.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_modules.append(node.module)
                self.assertFalse(
                    any(name.startswith("src.legacy.v1") for name in imported_modules),
                    f"当前主线不得导入旧版模块：{path}",
                )

    def test_legacy_source_does_not_import_current_business_packages(self):
        disallowed_prefixes = (
            "src.core",
            "src.pipeline",
            "src.modeling",
            "src.presentation",
            "src.web",
        )
        legacy_root = PROJECT_ROOT / "src" / "legacy" / "v1"

        for path in legacy_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)
            self.assertFalse(
                any(
                    name.startswith(disallowed_prefixes)
                    for name in imported_modules
                ),
                f"旧版不得导入当前业务模块：{path}",
            )

    def test_current_config_contains_no_legacy_sections_or_keys(self):
        config = yaml.safe_load(
            (PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8")
        )

        self.assertNotIn("paths", config)
        self.assertNotIn("spatial_data", config)
        self.assertNotIn("model_defaults", config)
        self.assertNotIn("convenience_store", config["weights"])
        self.assertNotIn("light_catering", config["weights"])

    def test_legacy_v1_has_independent_config_and_entry_modules(self):
        legacy_config = PROJECT_ROOT / "src" / "legacy" / "v1" / "config.yaml"
        self.assertTrue(legacy_config.is_file())
        config = yaml.safe_load(legacy_config.read_text(encoding="utf-8"))
        self.assertIn("paths", config)
        self.assertIn("spatial_data", config)
        self.assertIn("model_defaults", config)

        module_names = [
            "src.legacy.v1.app",
            "src.legacy.v1.config",
            "src.legacy.v1.osm.inventory",
            "src.legacy.v1.osm.pipeline",
            "src.legacy.v1.selection.two_stage",
        ]
        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))


if __name__ == "__main__":
    unittest.main()
