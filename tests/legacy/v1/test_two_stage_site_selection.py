import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiPoint, Point, Polygon

from src.legacy.v1.selection.two_stage import (
    build_metric_evaluation_grid,
    build_grid_stage_scoring_input,
    build_region_stage_scoring_input,
    filter_active_grids,
    run_region_stage_selection,
    score_spatial_business_types,
    select_regions_for_grid_stage,
)


class TwoStageSiteSelectionTests(unittest.TestCase):
    def test_region_stage_scoring_uses_density_not_raw_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            processed = base / "data" / "processed"
            processed.mkdir(parents=True)

            pd.DataFrame(
                [
                    {
                        "region_id": "small",
                        "school_count": 10,
                        "hospital_count": 2,
                        "bus_stop_count": 5,
                        "restaurant_count": 5,
                        "convenience_count": 1,
                        "supermarket_count": 1,
                        "mall_count": 1,
                        "office_count": 4,
                    },
                    {
                        "region_id": "large",
                        "school_count": 20,
                        "hospital_count": 4,
                        "bus_stop_count": 10,
                        "restaurant_count": 10,
                        "convenience_count": 2,
                        "supermarket_count": 2,
                        "mall_count": 2,
                        "office_count": 8,
                    },
                ]
            ).to_csv(processed / "poi_features.csv", index=False)
            pd.DataFrame(
                [
                    {"region_id": "small", "road_length_total": 5000, "road_density": 1000, "intersection_count": 5},
                    {"region_id": "large", "road_length_total": 10000, "road_density": 1000, "intersection_count": 10},
                ]
            ).to_csv(processed / "road_features.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "region_id": "small",
                        "residential_area": 100000,
                        "commercial_area": 50000,
                        "retail_area": 50000,
                        "industrial_area": 10000,
                        "farmland_area": 0,
                    },
                    {
                        "region_id": "large",
                        "residential_area": 200000,
                        "commercial_area": 100000,
                        "retail_area": 100000,
                        "industrial_area": 20000,
                        "farmland_area": 0,
                    },
                ]
            ).to_csv(processed / "landuse_features.csv", index=False)

            boundaries = gpd.GeoDataFrame(
                {
                    "region_id": ["small", "large"],
                    "region_name": ["小区域", "大区域"],
                },
                geometry=[
                    Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)]),
                    Polygon([(0, 0), (4000, 0), (4000, 4000), (0, 4000)]),
                ],
                crs="EPSG:3857",
            )

            result = build_region_stage_scoring_input(processed_dir=processed, regions=boundaries)

            small = result[result["region_id"].eq("small")].iloc[0]
            large = result[result["region_id"].eq("large")].iloc[0]
            self.assertGreater(small["school_density"], large["school_density"])
            self.assertGreaterEqual(small["consumption_potential"], large["consumption_potential"])
            for column in [
                "area_km2",
                "poi_density",
                "residential_landuse_ratio",
                "commercial_landuse_ratio",
                "retail_landuse_ratio",
                "synergy_score",
                "competition_pressure",
                "development_basis",
            ]:
                self.assertIn(column, result.columns)
            self.assertAlmostEqual(
                float(small["competition_pressure"]) + float(small["competition_pressure_reversed"]),
                1.0,
                places=6,
            )

    def test_score_spatial_business_types_outputs_rank_and_explanations(self):
        frame = pd.DataFrame(
            [
                {
                    "region_id": "r1",
                    "region_name": "区域1",
                    "traffic_accessibility": 1.0,
                    "consumption_potential": 0.9,
                    "synergy_business_score": 0.8,
                    "competition_pressure_reversed": 0.7,
                    "regional_development": 0.6,
                },
                {
                    "region_id": "r2",
                    "region_name": "区域2",
                    "traffic_accessibility": 0.1,
                    "consumption_potential": 0.2,
                    "synergy_business_score": 0.3,
                    "competition_pressure_reversed": 0.4,
                    "regional_development": 0.5,
                },
            ]
        )

        result = score_spatial_business_types(frame)

        self.assertEqual(result.loc[result["region_id"].eq("r1"), "rank_convenience"].iloc[0], 1)
        self.assertIn("main_advantage", result.columns)
        self.assertIn("main_risk", result.columns)
        self.assertIn("light_food_score", result.columns)
        self.assertTrue(result["main_advantage"].astype(str).str.len().gt(0).all())

    def test_run_region_stage_selection_returns_only_region_outputs(self):
        outputs = run_region_stage_selection(top_n=1)

        self.assertEqual(
            set(outputs.__dict__),
            {"region_stage_input", "region_stage_result", "selected_regions"},
        )
        self.assertTrue(outputs.region_stage_input.name.endswith("region_stage_scoring_input.csv"))
        self.assertTrue(outputs.region_stage_result.name.endswith("region_stage_score_result.csv"))
        self.assertTrue(outputs.selected_regions.name.endswith("selected_regions_for_grid_stage.csv"))

    def test_build_metric_evaluation_grid_creates_one_km_cells_inside_region(self):
        regions = gpd.GeoDataFrame(
            {"region_id": ["r1"], "region_name": ["区域1"]},
            geometry=[Polygon([(0, 0), (2500, 0), (2500, 1200), (0, 1200)])],
            crs="EPSG:3857",
        )

        grid = build_metric_evaluation_grid(regions, grid_size_m=1000)

        self.assertGreater(len(grid), 1)
        self.assertTrue(grid["grid_region_id"].eq("r1").all())
        self.assertTrue(grid["region_id"].str.startswith("grid_r1_").all())
        self.assertIn("grid_center_lon", grid.columns)
        self.assertIn("grid_center_lat", grid.columns)

    def test_grid_stage_scoring_input_contains_step5_alias_fields(self):
        grid = gpd.GeoDataFrame(
            {
                "region_id": ["grid_r1_000001"],
                "grid_region_id": ["r1"],
                "grid_region_name": ["区域1"],
                "grid_area_sq_km": [1.0],
                "grid_center_lon": [106.1],
                "grid_center_lat": [26.2],
            },
            geometry=[Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])],
            crs="EPSG:3857",
        )
        poi_features = pd.DataFrame(
            [
                {
                    "region_id": "grid_r1_000001",
                    "school_count": 1,
                    "hospital_count": 1,
                    "bus_stop_count": 1,
                    "restaurant_count": 1,
                    "convenience_count": 1,
                    "supermarket_count": 1,
                    "mall_count": 1,
                    "office_count": 1,
                }
            ]
        )
        road_features = pd.DataFrame(
            [
                {
                    "region_id": "grid_r1_000001",
                    "road_length_total": 1000.0,
                    "road_density": 1000.0,
                    "intersection_count": 2,
                }
            ]
        )
        landuse_features = pd.DataFrame(
            [
                {
                    "region_id": "grid_r1_000001",
                    "residential_area": 100.0,
                    "commercial_area": 100.0,
                    "retail_area": 100.0,
                    "industrial_area": 100.0,
                    "farmland_area": 0.0,
                }
            ]
        )

        result = build_grid_stage_scoring_input(grid, poi_features, road_features, landuse_features)

        required_columns = {
            "grid_id",
            "parent_region_id",
            "centroid_lon",
            "centroid_lat",
            "area_km2",
            "traffic_accessibility",
            "consumption_potential",
            "synergy_score",
            "competition_pressure",
            "development_basis",
        }
        self.assertTrue(required_columns.issubset(result.columns))
        row = result.iloc[0]
        self.assertEqual(row["grid_id"], row["region_id"])
        self.assertEqual(row["parent_region_id"], row["grid_region_id"])
        self.assertEqual(row["centroid_lon"], row["grid_center_lon"])
        self.assertEqual(row["centroid_lat"], row["grid_center_lat"])
        self.assertEqual(row["area_km2"], row["grid_area_sq_km"])

        scored = score_spatial_business_types(result)
        score_columns = {
            "convenience_score",
            "light_catering_score",
            "light_food_score",
            "rank_convenience",
            "rank_light_catering",
            "main_advantage",
            "main_risk",
        }
        self.assertTrue(score_columns.issubset(scored.columns))
        self.assertTrue(scored["main_advantage"].astype(str).str.len().gt(0).all())
        self.assertTrue(scored["main_risk"].astype(str).str.len().gt(0).all())

    def test_select_regions_for_grid_stage_limits_to_requested_region_id(self):
        score_result = pd.DataFrame(
            [
                {
                    "region_id": "r1",
                    "region_name": "区域1",
                    "convenience_score": 0.8,
                    "light_catering_score": 0.7,
                    "rank_convenience": 1,
                    "rank_light_catering": 2,
                    "main_advantage": "交通可达性",
                    "main_risk": "竞争压力较低",
                },
                {
                    "region_id": "r2",
                    "region_name": "区域2",
                    "convenience_score": 0.6,
                    "light_catering_score": 0.9,
                    "rank_convenience": 2,
                    "rank_light_catering": 1,
                    "main_advantage": "消费潜力",
                    "main_risk": "区域发展基础",
                },
            ]
        )

        selected = select_regions_for_grid_stage(score_result, top_n=2, region_ids=["r2"])

        self.assertEqual(selected["region_id"].tolist(), ["r2"])
        self.assertEqual(selected["selection_rank"].tolist(), [1])

    def test_filter_active_grids_keeps_grids_with_spatial_activity(self):
        frame = pd.DataFrame(
            [
                {"region_id": "grid_1", "school_count": 0, "road_length_total": 0, "residential_area": 0},
                {"region_id": "grid_2", "school_count": 1, "road_length_total": 0, "residential_area": 0},
                {"region_id": "grid_3", "school_count": 0, "road_length_total": 10, "residential_area": 0},
                {"region_id": "grid_4", "school_count": 0, "road_length_total": 0, "residential_area": 10},
            ]
        )

        result = filter_active_grids(frame)

        self.assertEqual(set(result["region_id"]), {"grid_2", "grid_3", "grid_4"})


if __name__ == "__main__":
    unittest.main()
