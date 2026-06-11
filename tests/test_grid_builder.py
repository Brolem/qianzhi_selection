import csv
import json
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from src import grid_builder


class GridBuilderTests(unittest.TestCase):
    def setUp(self):
        metric_boundaries = gpd.GeoDataFrame(
            {
                "district_name": ["测试一区", "测试二区"],
                "adcode": ["520101", "520102"],
            },
            geometry=[
                Polygon([(100, 100), (3100, 100), (3100, 3100), (100, 3100)]),
                Polygon([(3100, 100), (5100, 100), (5100, 2100), (3100, 2100)]),
            ],
            crs="EPSG:32648",
        )
        self.boundaries = metric_boundaries.to_crs("EPSG:4326")
        self.districts = pd.DataFrame(
            [
                {
                    "district_name": "测试一区",
                    "city_name": "贵阳市",
                    "adcode": "520101",
                    "center_lon": "",
                    "center_lat": "",
                    "has_boundary": True,
                    "data_source": "amap_api",
                },
                {
                    "district_name": "测试二区",
                    "city_name": "贵阳市",
                    "adcode": "520102",
                    "center_lon": "",
                    "center_lat": "",
                    "has_boundary": True,
                    "data_source": "amap_api",
                },
            ]
        )

    def test_build_aligned_cells_uses_one_kilometer_integer_axes(self):
        cells = grid_builder.build_aligned_cells((100, 100, 2100, 2100), grid_size_m=1000)

        self.assertEqual(cells[0][0:2], (0, 0))
        self.assertTrue(all(x % 1000 == 0 and y % 1000 == 0 for x, y, _ in cells))
        self.assertTrue(all(cell.bounds[2] - cell.bounds[0] == 1000 for _, _, cell in cells))
        self.assertTrue(all(cell.bounds[3] - cell.bounds[1] == 1000 for _, _, cell in cells))

    def test_generate_evaluation_grids_clips_edges_and_keeps_full_cells(self):
        grids = grid_builder.generate_evaluation_grids(
            self.boundaries,
            self.districts,
            grid_size_m=1000,
        )

        self.assertGreater(len(grids), 0)
        self.assertTrue(grids["area_km2"].gt(0).all())
        self.assertTrue(grids["area_km2"].le(1.0).all())
        self.assertTrue(grids["area_km2"].lt(1.0).any())
        self.assertTrue(grids["area_km2"].round(6).eq(1.0).any())
        self.assertTrue(grids["data_source"].eq("amap_boundary").all())

    def test_grid_ids_and_geometry_are_deterministic(self):
        first = grid_builder.generate_evaluation_grids(
            self.boundaries,
            self.districts,
            grid_size_m=1000,
        )
        second = grid_builder.generate_evaluation_grids(
            self.boundaries,
            self.districts,
            grid_size_m=1000,
        )

        self.assertEqual(first["grid_id"].tolist(), second["grid_id"].tolist())
        self.assertEqual(first.geometry.to_wkt().tolist(), second.geometry.to_wkt().tolist())
        self.assertTrue(first[first["adcode"] == "520101"]["grid_id"].str.startswith("grid_520101_").all())
        self.assertTrue(first[first["adcode"] == "520102"]["grid_id"].str.startswith("grid_520102_").all())

    def test_missing_boundary_uses_one_centered_demo_grid(self):
        center_metric = gpd.GeoSeries.from_xy([650000], [2940000], crs="EPSG:32648").to_crs("EPSG:4326").iloc[0]
        districts = pd.DataFrame(
            [
                {
                    "district_name": "测试三区",
                    "city_name": "贵阳市",
                    "adcode": "520103",
                    "center_lon": center_metric.x,
                    "center_lat": center_metric.y,
                    "has_boundary": False,
                    "data_source": "amap_api",
                }
            ]
        )
        empty_boundaries = gpd.GeoDataFrame(
            {"district_name": [], "adcode": []},
            geometry=[],
            crs="EPSG:4326",
        )

        grids = grid_builder.generate_evaluation_grids(
            empty_boundaries,
            districts,
            grid_size_m=1000,
        )

        self.assertEqual(len(grids), 1)
        self.assertEqual(grids.iloc[0]["grid_id"], "grid_520103_000001")
        self.assertEqual(grids.iloc[0]["data_source"], "demo_center")
        self.assertAlmostEqual(float(grids.iloc[0]["area_km2"]), 1.0, places=6)

    def test_write_grid_outputs_uses_exact_csv_and_geojson_schema(self):
        grids = grid_builder.generate_evaluation_grids(
            self.boundaries,
            self.districts,
            grid_size_m=1000,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = grid_builder.write_grid_outputs(grids, Path(tmp_dir))
            with outputs["csv"].open("r", encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            geojson = json.loads(outputs["geojson"].read_text(encoding="utf-8"))

        self.assertEqual(
            list(rows[0]),
            [
                "grid_id",
                "district_name",
                "adcode",
                "centroid_lon",
                "centroid_lat",
                "area_km2",
                "geometry_wkt",
                "data_source",
            ],
        )
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(geojson["coord_system"], "GCJ-02")
        self.assertNotIn("geometry_wkt", geojson["features"][0]["properties"])
        self.assertEqual(
            set(geojson["features"][0]["properties"]),
            {
                "grid_id",
                "district_name",
                "adcode",
                "centroid_lon",
                "centroid_lat",
                "area_km2",
                "data_source",
            },
        )


if __name__ == "__main__":
    unittest.main()
