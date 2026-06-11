import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.amap_client import AmapClient


class AmapClientTests(unittest.TestCase):
    def test_missing_amap_key_enters_demo_mode_without_crashing(self):
        with patch.dict(os.environ, {"AMAP_KEY": ""}):
            client = AmapClient()

        self.assertTrue(client.demo_mode)
        self.assertIsNone(client.get_district("云岩区", city="贵阳市"))
        self.assertIsNone(client.search_poi_around("106.713478,26.578343", "便利店"))
        self.assertIsNone(client.search_poi_polygon("106.7,26.5;106.8,26.5;106.8,26.6", "便利店"))

    def test_cache_key_is_stable_for_param_order(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)
            first_key = client._build_cache_key(
                "https://restapi.amap.com/v3/config/district",
                {"keywords": "云岩区", "city": "贵阳市"},
            )
            second_key = client._build_cache_key(
                "https://restapi.amap.com/v3/config/district",
                {"city": "贵阳市", "keywords": "云岩区"},
            )

        self.assertEqual(first_key, second_key)
        self.assertTrue(first_key.endswith(".json"))

    def test_get_district_constructs_expected_params(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)

            with patch.object(client, "_request_with_cache", return_value={"status": "1"}) as request:
                result = client.get_district("云岩区", city="贵阳市")

        self.assertEqual(result, {"status": "1"})
        url, params, cache_key = request.call_args.args
        self.assertEqual(url, "https://restapi.amap.com/v3/config/district")
        self.assertEqual(
            params,
            {
                "key": "test-key",
                "keywords": "云岩区",
                "subdistrict": 0,
                "extensions": "all",
                "output": "JSON",
                "city": "贵阳市",
            },
        )
        self.assertTrue(cache_key.endswith(".json"))

    def test_search_poi_methods_construct_expected_params(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)

            with patch.object(client, "_request_with_cache", return_value={"status": "1"}) as request:
                client.search_poi_around(
                    "106.713478,26.578343",
                    "便利店",
                    radius=800,
                    city="贵阳市",
                    page=2,
                    offset=10,
                )

            around_url, around_params, around_cache_key = request.call_args.args

            with patch.object(client, "_request_with_cache", return_value={"status": "1"}) as request:
                client.search_poi_polygon(
                    "106.7,26.5;106.8,26.5;106.8,26.6",
                    "便利店",
                    city="贵阳市",
                    page=3,
                    offset=20,
                )

            polygon_url, polygon_params, polygon_cache_key = request.call_args.args

        self.assertEqual(around_url, "https://restapi.amap.com/v5/place/around")
        self.assertEqual(
            around_params,
            {
                "key": "test-key",
                "location": "106.713478,26.578343",
                "keywords": "便利店",
                "radius": 800,
                "page_num": 2,
                "page_size": 10,
                "output": "JSON",
                "region": "贵阳市",
            },
        )
        self.assertTrue(around_cache_key.endswith(".json"))

        self.assertEqual(polygon_url, "https://restapi.amap.com/v5/place/polygon")
        self.assertEqual(
            polygon_params,
            {
                "key": "test-key",
                "polygon": "106.7,26.5;106.8,26.5;106.8,26.6",
                "keywords": "便利店",
                "page_num": 3,
                "page_size": 20,
                "output": "JSON",
                "region": "贵阳市",
            },
        )
        self.assertTrue(polygon_cache_key.endswith(".json"))

    def test_search_poi_around_accepts_typecodes_without_keywords(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)

            with patch.object(client, "_request_with_cache", return_value={"status": "1"}) as request:
                result = client.search_poi_around(
                    "106.713478,26.578343",
                    types="060200|060400",
                    radius=500,
                    city="贵阳市",
                    page=1,
                    offset=25,
                )

        self.assertEqual(result, {"status": "1"})
        url, params, cache_key = request.call_args.args
        self.assertEqual(url, "https://restapi.amap.com/v5/place/around")
        self.assertEqual(
            params,
            {
                "key": "test-key",
                "location": "106.713478,26.578343",
                "types": "060200|060400",
                "radius": 500,
                "page_num": 1,
                "page_size": 25,
                "output": "JSON",
                "region": "贵阳市",
            },
        )
        self.assertTrue(cache_key.endswith(".json"))

    def test_search_poi_around_requires_keywords_or_typecodes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)

            with self.assertRaisesRegex(ValueError, "keywords.*types"):
                client.search_poi_around("106.713478,26.578343")

    def test_request_with_cache_uses_existing_json_without_network(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)
            cache_path = Path(tmp_dir) / "cached-response.json"
            expected = {"status": "1", "districts": []}
            cache_path.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")

            with patch("src.amap_client.urlopen") as urlopen:
                result = client._request_with_cache(
                    "https://restapi.amap.com/v3/config/district",
                    {"keywords": "云岩区"},
                    "cached-response.json",
                )

        self.assertEqual(result, expected)
        urlopen.assert_not_called()

    def test_request_failure_returns_none_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = AmapClient(api_key="test-key", cache_dir=tmp_dir)

            with self.assertLogs("src.amap_client", level="WARNING"):
                with patch("src.amap_client.urlopen", side_effect=OSError("network unavailable")):
                    result = client._request_with_cache(
                        "https://restapi.amap.com/v3/config/district",
                        {"keywords": "云岩区"},
                        "failed-response.json",
                    )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
