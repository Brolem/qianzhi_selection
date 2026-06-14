from pathlib import Path
import unittest

from src.legacy.v1 import config as legacy_config


class LegacyConfigTests(unittest.TestCase):
    def test_legacy_paths_are_isolated_from_current_data_and_outputs(self):
        root = Path.cwd()

        self.assertEqual(
            legacy_config.get_path("raw_osm_data"),
            root / "data/legacy/v1/raw/osm_guizhou",
        )
        self.assertEqual(
            legacy_config.get_path("processed_osm_region"),
            root / "data/legacy/v1/processed/osm_region",
        )
        self.assertEqual(
            legacy_config.get_path("processed_site_selection"),
            root / "data/legacy/v1/processed/site_selection",
        )
        self.assertEqual(
            legacy_config.get_path("results_grid_stage"),
            root / "outputs/legacy/v1/results/grid_stage",
        )
        self.assertEqual(
            legacy_config.get_path("reports"),
            root / "outputs/legacy/v1/reports",
        )


if __name__ == "__main__":
    unittest.main()
