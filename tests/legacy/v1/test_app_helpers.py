import tempfile
from pathlib import Path
import unittest

import pandas as pd

from src.legacy.v1.app import (
    business_columns,
    load_table,
    map_file_for_business,
    top_rows,
)


class LegacyAppHelperTests(unittest.TestCase):
    def test_business_columns_returns_exact_fields_for_supported_business_types(self):
        self.assertEqual(
            business_columns("社区便利店"),
            ("convenience_score", "rank_convenience"),
        )
        self.assertEqual(
            business_columns("轻餐饮"),
            ("light_catering_score", "rank_light_catering"),
        )

    def test_business_columns_rejects_unknown_business_type(self):
        with self.assertRaises(ValueError):
            business_columns("其他")

    def test_top_rows_sorts_by_rank_column_ascending(self):
        frame = pd.DataFrame(
            [
                {"grid_id": "grid_2", "rank_convenience": 2},
                {"grid_id": "grid_1", "rank_convenience": 1},
                {"grid_id": "grid_3", "rank_convenience": 3},
            ]
        )

        result = top_rows(frame, "rank_convenience", 2)

        self.assertEqual(result["grid_id"].tolist(), ["grid_1", "grid_2"])

    def test_map_file_for_business_returns_v1_html_paths(self):
        self.assertEqual(
            map_file_for_business("社区便利店").name,
            "convenience_grid_map.html",
        )
        self.assertEqual(
            map_file_for_business("轻餐饮").name,
            "light_food_grid_map.html",
        )

    def test_load_table_reads_csv_and_requires_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "table.csv"
            pd.DataFrame([{"region_id": "8316193"}]).to_csv(
                csv_path,
                index=False,
                encoding="utf-8-sig",
            )

            loaded = load_table(csv_path)

            self.assertEqual(
                loaded["region_id"].astype(str).tolist(),
                ["8316193"],
            )
            with self.assertRaises(FileNotFoundError):
                load_table(Path(tmp_dir) / "missing.csv")


if __name__ == "__main__":
    unittest.main()
