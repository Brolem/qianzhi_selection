import tempfile
import unittest
from pathlib import Path

from src import config as config_module


class ConfigHelperTests(unittest.TestCase):
    def test_v2_config_sections_and_values_are_present(self):
        cfg = config_module.load_config()

        self.assertEqual(cfg["project"]["name"], "黔址优选")
        self.assertEqual(cfg["project"]["city"], "贵阳市")
        self.assertEqual(cfg["project"]["grid_size_m"], 1000)
        self.assertEqual(cfg["project"]["default_radius_m"], 500)
        self.assertEqual(cfg["project"]["optional_radius_m"], [500, 800, 1000])
        self.assertEqual(cfg["target_districts"]["first_version"], ["云岩区", "南明区", "观山湖区"])
        self.assertEqual(cfg["target_districts"]["optional_enhancement"], ["花溪区", "白云区"])

        for key in [
            "official_raw_dir",
            "processed_dir",
            "results_dir",
            "reports_dir",
            "figures_dir",
            "amap_cache_dir",
            "demo_dir",
        ]:
            self.assertIn(key, cfg["data_paths"])

    def test_get_project_root_and_get_path_support_v2_and_legacy_paths(self):
        root = config_module.get_project_root()

        self.assertEqual(root, Path.cwd())
        self.assertEqual(config_module.get_path("official_raw_dir"), root / "data/raw/official")
        self.assertEqual(config_module.get_path("results_grid_stage"), root / "outputs/results/grid_stage")

    def test_get_weights_accepts_config_first_or_business_type_first(self):
        cfg = config_module.load_config()
        expected_keys = {
            "traffic_accessibility",
            "consumption_potential",
            "employment_customer_proxy",
            "synergy_score",
            "competition_pressure",
            "business_atmosphere",
        }

        convenience = config_module.get_weights(cfg, "convenience")
        light_food = config_module.get_weights("light_food")

        self.assertEqual(set(convenience), expected_keys)
        self.assertEqual(set(light_food), expected_keys)
        self.assertAlmostEqual(sum(convenience.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(light_food.values()), 1.0, places=6)

    def test_get_poi_categories_returns_exact_step2_categories(self):
        categories = config_module.get_poi_categories()

        self.assertEqual(
            categories,
            {
                "convenience_store": "便利店",
                "supermarket": "超市",
                "restaurant": "餐饮",
                "fast_food": "快餐",
                "snack": "小吃",
                "cafe": "咖啡",
                "tea": "茶饮",
                "school": "学校",
                "hospital": "医院",
                "mall": "商场",
                "office": "写字楼",
                "residential": "小区",
                "bus_stop": "公交站",
                "subway_station": "地铁站",
                "parking": "停车场",
            },
        )

    def test_get_poi_typecodes_returns_exact_comparison_categories(self):
        typecodes = config_module.get_poi_typecodes()

        self.assertEqual(
            typecodes,
            {
                "convenience_store": "060200",
                "supermarket": "060400",
                "restaurant": "050000",
                "fast_food": "050300",
                "snack": "050400|050800|050900",
                "cafe": "050500",
                "tea": "050700",
                "school": "141200",
                "hospital": "090100|090200",
                "mall": "060100",
                "office": "120201",
                "residential": "120300",
                "bus_stop": "150700",
                "subway_station": "150500",
                "parking": "150900",
            },
        )

    def test_ensure_dirs_creates_v2_data_paths_without_requiring_repo_writes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            cfg = {
                "data_paths": {
                    "processed_dir": str(base / "processed"),
                    "results_dir": str(base / "results"),
                    "reports_dir": str(base / "reports"),
                    "figures_dir": str(base / "figures"),
                    "amap_cache_dir": str(base / "cache" / "amap"),
                    "demo_dir": str(base / "demo"),
                }
            }

            config_module.ensure_dirs(cfg)

            for path in cfg["data_paths"].values():
                self.assertTrue(Path(path).is_dir())

    def test_missing_path_and_weight_keys_raise_clear_errors(self):
        with self.assertRaisesRegex(KeyError, "missing_path"):
            config_module.get_path("missing_path", {"data_paths": {}, "paths": {}})

        with self.assertRaisesRegex(KeyError, "missing_business"):
            config_module.get_weights({"weights": {}}, "missing_business")


if __name__ == "__main__":
    unittest.main()
