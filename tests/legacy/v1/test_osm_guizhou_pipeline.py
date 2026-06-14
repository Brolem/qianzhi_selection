import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from src.legacy.v1.osm.pipeline import (
    build_grid_regions,
    classify_poi_counts,
    classify_road_type,
    pick_first_layer_name,
    write_layer_inventory,
)


class OsmGuizhouPipelineTests(unittest.TestCase):
    def test_classify_poi_counts_from_real_columns(self):
        regions = gpd.GeoDataFrame(
            {"region_id": ["r1"], "region_name": ["区域1"]},
            geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
            crs="EPSG:4326",
        )
        pois = gpd.GeoDataFrame(
            {
                "fclass": ["school", "hospital", "restaurant", "convenience", "supermarket", "mall", "office"],
                "name": ["学校", "医院", "餐饮", "便利店", "超市", "商场", "办公"],
            },
            geometry=[
                Point(0.2, 0.2),
                Point(0.3, 0.3),
                Point(0.4, 0.4),
                Point(0.5, 0.5),
                Point(0.6, 0.6),
                Point(0.7, 0.7),
                Point(0.8, 0.8),
            ],
            crs="EPSG:4326",
        )

        result = classify_poi_counts(pois, regions)

        self.assertEqual(result.loc[0, "school_count"], 1)
        self.assertEqual(result.loc[0, "hospital_count"], 1)
        self.assertEqual(result.loc[0, "restaurant_count"], 1)
        self.assertEqual(result.loc[0, "convenience_count"], 1)
        self.assertEqual(result.loc[0, "supermarket_count"], 1)
        self.assertEqual(result.loc[0, "mall_count"], 1)
        self.assertEqual(result.loc[0, "office_count"], 1)

    def test_build_grid_regions_creates_multiple_internal_regions(self):
        source = gpd.GeoDataFrame(
            {"name": ["范围"]},
            geometry=[Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])],
            crs="EPSG:4326",
        )

        grid = build_grid_regions(source, grid_size_degrees=1.0)

        self.assertGreater(len(grid), 1)
        self.assertTrue(grid["region_id"].str.startswith("grid_").all())

    def test_classify_road_type_uses_exact_fclass_values(self):
        self.assertEqual(classify_road_type("primary"), "main")
        self.assertEqual(classify_road_type("secondary"), "secondary")
        self.assertEqual(classify_road_type("residential"), "local")
        self.assertEqual(classify_road_type("footway"), "walk")
        self.assertEqual(classify_road_type("unknown"), "")

    def test_write_layer_inventory_records_layer_names(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "layers.csv"

            write_layer_inventory(
                [{"layer_name": "gis_osm_pois_free_1", "feature_count": 10, "columns": "fclass,name"}],
                path,
            )

            self.assertIn("gis_osm_pois_free_1", path.read_text(encoding="utf-8-sig"))

    def test_pick_first_layer_name_accepts_adminareas_for_boundaries(self):
        inventory = [
            {"layer_name": "gis_osm_roads_free"},
            {"layer_name": "gis_osm_adminareas_a_free"},
        ]

        self.assertEqual(
            pick_first_layer_name(inventory, ["boundaries", "adminareas"]),
            "gis_osm_adminareas_a_free",
        )


if __name__ == "__main__":
    unittest.main()
