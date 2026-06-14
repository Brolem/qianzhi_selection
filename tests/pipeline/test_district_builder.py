import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.pipeline import district_builder


class FakeAmapClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_district(self, keyword, city=None):
        self.calls.append((keyword, city))
        return self.responses.get(keyword)


class DistrictBuilderTests(unittest.TestCase):
    def test_parse_center_splits_lon_and_lat(self):
        lon, lat = district_builder.parse_center("106.713478,26.578343")

        self.assertEqual(lon, 106.713478)
        self.assertEqual(lat, 26.578343)

    def test_parse_polyline_returns_polygon_geometry(self):
        geometry = district_builder.parse_polyline(
            "106.700000,26.500000;106.800000,26.500000;106.800000,26.600000;106.700000,26.600000"
        )

        self.assertEqual(geometry["type"], "Polygon")
        self.assertEqual(geometry["coordinates"][0][0], [106.7, 26.5])
        self.assertEqual(geometry["coordinates"][0][-1], [106.7, 26.5])

    def test_parse_polyline_returns_multi_polygon_for_multiple_parts(self):
        geometry = district_builder.parse_polyline(
            "106.700000,26.500000;106.800000,26.500000;106.800000,26.600000"
            "|106.900000,26.700000;107.000000,26.700000;107.000000,26.800000"
        )

        self.assertEqual(geometry["type"], "MultiPolygon")
        self.assertEqual(len(geometry["coordinates"]), 2)

    def test_build_target_district_outputs_csv_geojson_and_warning(self):
        responses = {
            "云岩区": {
                "status": "1",
                "info": "OK",
                "infocode": "10000",
                "districts": [
                    {
                        "name": "云岩区",
                        "adcode": "520103",
                        "center": "106.713478,26.578343",
                        "polyline": (
                            "106.700000,26.500000;106.800000,26.500000;"
                            "106.800000,26.600000;106.700000,26.600000"
                        ),
                        "level": "district",
                    }
                ],
            },
            "南明区": {
                "status": "1",
                "info": "OK",
                "infocode": "10000",
                "districts": [
                    {
                        "name": "南明区",
                        "adcode": "520102",
                        "center": "106.714374,26.568257",
                        "polyline": "",
                        "level": "district",
                    }
                ],
            },
        }
        cfg = {
            "project": {"city": "贵阳市"},
            "target_districts": {"first_version": ["云岩区", "南明区"]},
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            outputs = district_builder.build_target_districts(
                config=cfg,
                client=FakeAmapClient(responses),
                processed_dir=base / "processed",
                results_dir=base / "results",
            )

            with outputs["districts_csv"].open("r", encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            geojson = json.loads(outputs["boundaries_geojson"].read_text(encoding="utf-8"))
            warning_text = outputs["warnings_md"].read_text(encoding="utf-8")

        self.assertEqual(
            list(rows[0].keys()),
            [
                "district_name",
                "city_name",
                "adcode",
                "center_lon",
                "center_lat",
                "has_boundary",
                "data_source",
            ],
        )
        self.assertEqual(rows[0]["district_name"], "云岩区")
        self.assertEqual(rows[0]["city_name"], "贵阳市")
        self.assertEqual(rows[0]["adcode"], "520103")
        self.assertEqual(rows[0]["has_boundary"], "True")
        self.assertEqual(rows[0]["data_source"], "amap_api")
        self.assertEqual(rows[1]["district_name"], "南明区")
        self.assertEqual(rows[1]["has_boundary"], "False")

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(geojson["features"][0]["properties"], {"district_name": "云岩区", "adcode": "520103"})
        self.assertEqual(geojson["features"][0]["geometry"]["type"], "Polygon")
        self.assertIn("南明区", warning_text)
        self.assertIn("缺少 polyline", warning_text)


if __name__ == "__main__":
    unittest.main()
