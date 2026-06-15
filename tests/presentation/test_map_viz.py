import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.presentation import map_viz


WEIGHTS = {
    "traffic_accessibility": 0.20,
    "consumption_potential": 0.25,
    "employment_customer_proxy": 0.10,
    "synergy_score": 0.20,
    "competition_pressure": 0.15,
    "business_atmosphere": 0.10,
}


def write_metadata(path: Path, profiles: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": profiles,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


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
                "convenience_demand_customer_proxy": score,
                "convenience_market_stage": (
                    "成熟商圈型" if active else "无 POI 活动"
                ),
                "convenience_competition_alert": (
                    "过度竞争预警" if active else "不参与诊断"
                ),
                "convenience_diagnosis_summary": (
                    "成熟商圈型；过度竞争预警"
                    if active
                    else "无 POI 活动；不参与诊断"
                ),
                "light_food_score": score,
                "light_food_rank": rank,
                "light_food_district_rank": rank,
                "light_food_main_advantage": "就业客群代理" if active else "未检测到POI活动",
                "light_food_main_risk": "交通可达性不足" if active else "缺少可用于推荐的POI活动",
                "light_food_recommendation_level": "推荐" if rank == 1 else "暂不推荐",
                "light_food_demand_customer_proxy": score,
                "light_food_market_stage": (
                    "成熟商圈型" if active else "无 POI 活动"
                ),
                "light_food_competition_alert": (
                    "过度竞争预警" if active else "不参与诊断"
                ),
                "light_food_diagnosis_summary": (
                    "成熟商圈型；过度竞争预警"
                    if active
                    else "无 POI 活动；不参与诊断"
                ),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    write_metadata(
        path.parent / "profile_metadata.json",
        [
            {
                "profile_id": "convenience",
                "profile_name": "社区便利店",
                "template_id": "community_retail",
                "weights": WEIGHTS,
            },
            {
                "profile_id": "light_food",
                "profile_name": "轻餐饮",
                "template_id": "food_service",
                "weights": WEIGHTS,
            },
        ],
    )
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
    custom["profile_demand_customer_proxy"] = [82.0, 0.0, 34.0]
    custom["profile_market_stage"] = ["成熟商圈型", "无 POI 活动", "一般观察型"]
    custom["profile_competition_alert"] = ["过度竞争预警", "不参与诊断", "未触发过度竞争预警"]
    custom["profile_diagnosis_summary"] = [
        "成熟商圈型；过度竞争预警",
        "无 POI 活动；不参与诊断",
        "一般观察型；未触发过度竞争预警",
    ]
    custom.to_csv(path, index=False, encoding="utf-8-sig")
    write_metadata(
        path.parent / "profile_metadata.json",
        [
            {
                "profile_id": profile_id,
                "profile_name": "自定义社区业态",
                "template_id": "community_retail",
                "weights": WEIGHTS,
            }
        ],
    )
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
    def test_amap_credentials_use_explicit_values_then_environment(self):
        explicit = map_viz.load_amap_js_credentials(
            api_key="explicit-key",
            security_code="explicit-code",
        )
        self.assertEqual(explicit.api_key, "explicit-key")
        self.assertEqual(explicit.security_code, "explicit-code")

        with patch.dict(
            os.environ,
            {
                "AMAP_JS_KEY": "environment-key",
                "AMAP_JS_SECURITY_CODE": "environment-code",
            },
            clear=False,
        ):
            environment = map_viz.load_amap_js_credentials()

        self.assertEqual(environment.api_key, "environment-key")
        self.assertEqual(environment.security_code, "environment-code")

    def test_amap_credentials_allow_absent_pair_and_reject_partial_pair(self):
        with patch.dict(
            os.environ,
            {"AMAP_JS_KEY": "", "AMAP_JS_SECURITY_CODE": ""},
            clear=False,
        ):
            self.assertIsNone(map_viz.load_amap_js_credentials())

        with patch.dict(
            os.environ,
            {
                "AMAP_JS_KEY": "visible-key",
                "AMAP_JS_SECURITY_CODE": "",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "AMAP_JS_SECURITY_CODE",
            ) as context:
                map_viz.load_amap_js_credentials()
        self.assertNotIn("visible-key", str(context.exception))

    def test_default_profile_specs_use_exact_step8_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            specs = map_viz.default_profile_specs(result_path)

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

    def test_folium_map_center_uses_converted_latitude_longitude_order(self):
        frame = pd.DataFrame(
            {
                "centroid_lon": [106.70, 106.72],
                "centroid_lat": [26.60, 26.62],
            }
        )
        converted = [
            map_viz.gcj02_to_wgs84(106.70, 26.60),
            map_viz.gcj02_to_wgs84(106.72, 26.62),
        ]

        center = map_viz._map_center(frame)

        self.assertAlmostEqual(
            center[0],
            sum(lat for _, lat in converted) / 2,
        )
        self.assertAlmostEqual(
            center[1],
            sum(lon for lon, _ in converted) / 2,
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
            self.assertIn("map_market_stage", html)
            self.assertIn("map_competition_alert", html)
            self.assertIn("metric_consumption", html)
            self.assertIn("top-rank-badge", html)
            self.assertIn("pointer-events:none", html)

    def test_prepare_amap_payload_keeps_gcj02_and_four_map_states(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            spec = map_viz.default_profile_specs(result_path)["convenience"]
            source = json.loads(geojson_path.read_text(encoding="utf-8"))

            payload = map_viz.prepare_amap_payload(
                spec,
                geojson_path=geojson_path,
                top_n=10,
            )

            self.assertEqual(payload["coord_system"], "GCJ-02")
            self.assertEqual(
                payload["geojson"]["features"][0]["geometry"]["coordinates"],
                source["features"][0]["geometry"]["coordinates"],
            )
            self.assertEqual(
                payload["status_counts"],
                {"uncollected": 1, "inactive": 1, "active": 2, "top": 1},
            )
            self.assertEqual(len(payload["top_markers"]), 1)
            self.assertEqual(payload["top_markers"][0]["rank"], 1)
            first = payload["geojson"]["features"][0]["properties"]
            self.assertEqual(first["map_market_stage"], "成熟商圈型")
            self.assertEqual(first["map_competition_alert"], "过度竞争预警")

    def test_build_amap_map_html_contains_loader_interactions_and_safe_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            spec = map_viz.default_profile_specs(result_path)["convenience"]
            credentials = map_viz.AmapJsCredentials(
                api_key="test-js-key",
                security_code="test-security-code",
            )

            html = map_viz.build_amap_map_html(
                spec,
                credentials=credentials,
                geojson_path=geojson_path,
                map_config={
                    "provider": "amap_js",
                    "js_api_version": "2.0",
                    "map_style": "amap://styles/whitesmoke",
                    "default_zoom": 11,
                    "height": 680,
                    "top_n": 10,
                    "enable_folium_fallback": True,
                },
            )

            self.assertIn("https://webapi.amap.com/loader.js", html)
            self.assertIn("securityJsCode", html)
            self.assertIn("test-js-key", html)
            self.assertIn("test-security-code", html)
            self.assertIn('version:"2.0"', html)
            self.assertIn("AMap.Polygon", html)
            self.assertIn("mouseover", html)
            self.assertIn("mouseout", html)
            self.assertIn("click", html)
            self.assertIn("top-rank-badge", html)
            self.assertIn("社区便利店评分图例", html)
            self.assertIn("市场阶段", html)
            self.assertIn("竞争状态", html)
            self.assertIn("GCJ-02", html)
            self.assertNotIn(">60-80<", html)
            self.assertNotIn(">80-100<", html)
            self.assertIn(
                '<b class="legend-top-rank">1</b>全局 Top 10',
                html,
            )
            self.assertNotIn("</script><script>", html)

    def test_folium_legend_keeps_zero_to_sixty_and_numbered_top_marker(self):
        legend = map_viz._legend_html(
            "社区便利店",
            include_uncollected=True,
        )

        self.assertIn(">0-20<", legend)
        self.assertIn(">20-40<", legend)
        self.assertIn(">40-60<", legend)
        self.assertNotIn(">60-80<", legend)
        self.assertNotIn(">80-100<", legend)
        self.assertIn(
            '<b class="legend-top-rank">1</b>全局 Top 10',
            legend,
        )

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
                "src.presentation.map_viz.os.replace",
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

    def test_write_default_maps_uses_amap_with_credentials_and_folium_without(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = make_default_result(base / "result.csv")
            geojson_path = make_geojson(base / "grids.geojson")
            amap_dir = base / "amap"
            folium_dir = base / "folium"
            credentials = map_viz.AmapJsCredentials(
                api_key="test-js-key",
                security_code="test-security-code",
            )

            amap_paths = map_viz.write_default_maps(
                result_path=result_path,
                geojson_path=geojson_path,
                output_dir=amap_dir,
                credentials=credentials,
            )
            folium_paths = map_viz.write_default_maps(
                result_path=result_path,
                geojson_path=geojson_path,
                output_dir=folium_dir,
                credentials=None,
            )

            self.assertIn(
                "https://webapi.amap.com/loader.js",
                amap_paths[0].read_text(encoding="utf-8"),
            )
            self.assertIn(
                "leaflet",
                folium_paths[0].read_text(encoding="utf-8").lower(),
            )


if __name__ == "__main__":
    unittest.main()
