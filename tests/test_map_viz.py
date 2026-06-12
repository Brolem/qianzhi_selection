import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.visualization import map_viz


def make_default_result(path: Path) -> Path:
    rows = []
    for index, active in enumerate([True, False, True], start=1):
        score = [83.0, 0.0, 35.0][index - 1]
        rank = [1, None, 11][index - 1]
        rows.append(
            {
                "grid_id": f"grid_{index}",
                "district_name": "测试区",
                "centroid_lon": 106.70 + index * 0.01,
                "centroid_lat": 26.60 + index * 0.01,
                "has_poi_activity": active,
                "traffic_accessibility": score,
                "consumption_potential": score,
                "employment_customer_proxy": score,
                "business_atmosphere": score,
                "convenience_synergy_score": score,
                "light_food_synergy_score": score,
                "convenience_competition_score": 60.0 if active else 100.0,
                "light_food_competition_score": 55.0 if active else 100.0,
                "convenience_score": score,
                "convenience_rank": rank,
                "convenience_district_rank": rank,
                "convenience_main_advantage": "消费潜力" if active else "未检测到POI活动",
                "convenience_main_risk": "竞争压力较高" if active else "缺少可用于推荐的POI活动",
                "convenience_recommendation_level": "推荐" if rank == 1 else "暂不推荐",
                "light_food_score": score,
                "light_food_rank": rank,
                "light_food_district_rank": rank,
                "light_food_main_advantage": "就业客群代理" if active else "未检测到POI活动",
                "light_food_main_risk": "交通可达性不足" if active else "缺少可用于推荐的POI活动",
                "light_food_recommendation_level": "推荐" if rank == 1 else "暂不推荐",
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def make_custom_result(path: Path, profile_id: str = "custom_01") -> Path:
    frame = pd.read_csv(make_default_result(path.parent / "default.csv"))
    custom = frame[
        [
            "grid_id",
            "district_name",
            "centroid_lon",
            "centroid_lat",
            "has_poi_activity",
            "traffic_accessibility",
            "consumption_potential",
            "employment_customer_proxy",
            "business_atmosphere",
            "convenience_synergy_score",
        ]
    ].copy()
    custom["profile_id"] = profile_id
    custom["profile_name"] = "自定义社区业态"
    custom["template_id"] = "community_retail"
    custom["profile_competition_score"] = [60.0, 100.0, 50.0]
    custom["profile_score"] = [82.0, 0.0, 34.0]
    custom["profile_rank"] = [1, None, 11]
    custom["district_profile_rank"] = [1, None, 2]
    custom["profile_main_advantage"] = ["消费潜力", "未检测到POI活动", "交通可达性"]
    custom["profile_main_risk"] = ["竞争压力较高", "缺少可用于推荐的POI活动", "消费潜力不足"]
    custom["profile_recommendation_level"] = ["推荐", "暂不推荐", "暂不推荐"]
    custom.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def square(lon: float, lat: float) -> list[list[list[float]]]:
    return [
        [
            [lon, lat],
            [lon + 0.01, lat],
            [lon + 0.01, lat + 0.01],
            [lon, lat + 0.01],
            [lon, lat],
        ]
    ]


def make_geojson(path: Path) -> Path:
    features = []
    for index in range(1, 5):
        geometry = {
            "type": "Polygon" if index < 4 else "MultiPolygon",
            "coordinates": square(106.60 + index * 0.02, 26.50 + index * 0.02),
        }
        if index == 4:
            geometry["coordinates"] = [geometry["coordinates"]]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "grid_id": f"grid_{index}",
                    "district_name": "测试区",
                },
                "geometry": geometry,
            }
        )
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "coord_system": "GCJ-02",
                "features": features,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


class MapVizTests(unittest.TestCase):
    def test_default_profile_specs_use_exact_step8_fields(self):
        specs = map_viz.default_profile_specs(Path("result.csv"))

        self.assertEqual(specs["convenience"].score_field, "convenience_score")
        self.assertEqual(specs["convenience"].synergy_field, "convenience_synergy_score")
        self.assertEqual(specs["light_food"].rank_field, "light_food_rank")
        self.assertEqual(specs["light_food"].competition_score_field, "light_food_competition_score")

    def test_discover_custom_profile_specs_uses_file_metadata_and_stable_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            profile_dir = base / "custom_01"
            profile_dir.mkdir()
            make_custom_result(profile_dir / "grid_score_result.csv")

            specs = map_viz.discover_custom_profile_specs(base)

            self.assertEqual(list(specs), ["custom_01"])
            spec = specs["custom_01"]
            self.assertEqual(spec.profile_name, "自定义社区业态")
            self.assertEqual(spec.template_id, "community_retail")
            self.assertEqual(spec.score_field, "profile_score")
            self.assertEqual(spec.synergy_field, "convenience_synergy_score")

    def test_custom_profile_directory_and_metadata_must_match(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            profile_dir = base / "folder_id"
            profile_dir.mkdir()
            make_custom_result(
                profile_dir / "grid_score_result.csv",
                profile_id="file_id",
            )

            with self.assertRaisesRegex(ValueError, "folder_id"):
                map_viz.discover_custom_profile_specs(base)

    def test_gcj02_conversion_round_trip_and_outside_china(self):
        gcj_lon, gcj_lat = 116.397128, 39.916527
        wgs_lon, wgs_lat = map_viz.gcj02_to_wgs84(gcj_lon, gcj_lat)
        round_lon, round_lat = map_viz.wgs84_to_gcj02(wgs_lon, wgs_lat)

        self.assertAlmostEqual(round_lon, gcj_lon, places=5)
        self.assertAlmostEqual(round_lat, gcj_lat, places=5)
        self.assertEqual(
            map_viz.gcj02_to_wgs84(-73.9857, 40.7484),
            (-73.9857, 40.7484),
        )

    def test_convert_geojson_to_wgs84_handles_polygon_and_multipolygon(self):
        source = {
            "type": "FeatureCollection",
            "coord_system": "GCJ-02",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"grid_id": "polygon"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": square(106.7, 26.6),
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"grid_id": "multi"},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [square(106.8, 26.7)],
                    },
                },
            ],
        }

        converted = map_viz.convert_geojson_to_wgs84(source)

        self.assertEqual(converted["coord_system"], "WGS84")
        self.assertNotEqual(
            converted["features"][0]["geometry"]["coordinates"][0][0],
            source["features"][0]["geometry"]["coordinates"][0][0],
        )
        self.assertNotEqual(
            converted["features"][1]["geometry"]["coordinates"][0][0][0],
            source["features"][1]["geometry"]["coordinates"][0][0][0],
        )
        self.assertEqual(source["coord_system"], "GCJ-02")

    def test_score_color_uses_fixed_boundaries(self):
        self.assertEqual(map_viz.score_color(0), "#B34A42")
        self.assertEqual(map_viz.score_color(19.999), "#B34A42")
        self.assertEqual(map_viz.score_color(20), "#D98252")
        self.assertEqual(map_viz.score_color(40), "#E8B96B")
        self.assertEqual(map_viz.score_color(60), "#5FA27C")
        self.assertEqual(map_viz.score_color(80), "#176B4A")
        self.assertEqual(map_viz.score_color(100), "#176B4A")

    def test_build_profile_map_renders_four_states_and_top_marker(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            spec = map_viz.default_profile_specs(result_path)["convenience"]

            result_map = map_viz.build_profile_map(
                spec,
                geojson_path=geojson_path,
                top_n=10,
            )
            html = result_map.get_root().render()

            self.assertEqual(
                result_map._qianzhi_status_counts,
                {"uncollected": 1, "inactive": 1, "active": 2, "top": 1},
            )
            self.assertIn("未采集", html)
            self.assertIn("无 POI 活动", html)
            self.assertIn("grid_1", html)
            self.assertIn("map_advantage", html)
            self.assertIn("map_risk", html)
            self.assertIn("map_level", html)
            self.assertIn("metric_consumption", html)
            self.assertIn("top-rank-badge", html)
            self.assertIn("pointer-events:none", html)

    def test_build_profile_map_falls_back_to_scored_centroids(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            spec = map_viz.default_profile_specs(result_path)["light_food"]

            result_map = map_viz.build_profile_map(
                spec,
                geojson_path=base / "missing.geojson",
            )
            html = result_map.get_root().render()

            self.assertIn("当前仅展示评分网格中心点", html)
            self.assertIn("grid_1", html)
            self.assertNotIn("未采集网格", html)

    def test_scored_grid_missing_from_geojson_stops_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            data = json.loads(geojson_path.read_text(encoding="utf-8"))
            data["features"] = [
                feature
                for feature in data["features"]
                if feature["properties"]["grid_id"] != "grid_3"
            ]
            geojson_path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
            spec = map_viz.default_profile_specs(result_path)["convenience"]

            with self.assertRaisesRegex(ValueError, "grid_3"):
                map_viz.build_profile_map(spec, geojson_path=geojson_path)

    def test_second_html_replace_failure_restores_both_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            output_dir = base / "figures"
            output_dir.mkdir()
            convenience_path = output_dir / "convenience_grid_map.html"
            light_food_path = output_dir / "light_food_grid_map.html"
            convenience_path.write_text("existing convenience", encoding="utf-8")
            light_food_path.write_text("existing light food", encoding="utf-8")
            real_replace = os.replace
            call_count = 0

            def fail_second_replace(source, target):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("simulated second map replace failure")
                return real_replace(source, target)

            with patch(
                "src.visualization.map_viz.os.replace",
                side_effect=fail_second_replace,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated second map replace failure",
                ):
                    map_viz.write_default_maps(
                        result_path=result_path,
                        geojson_path=geojson_path,
                        output_dir=output_dir,
                    )

            self.assertEqual(
                convenience_path.read_text(encoding="utf-8"),
                "existing convenience",
            )
            self.assertEqual(
                light_food_path.read_text(encoding="utf-8"),
                "existing light food",
            )


if __name__ == "__main__":
    unittest.main()
