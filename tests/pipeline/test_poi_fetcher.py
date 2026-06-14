import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.pipeline import poi_fetcher


POI_CATEGORIES = {
    "convenience_store": "便利店",
    "supermarket": "超市",
    "restaurant": "餐饮",
}


class StubAmapClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.api_key = "test-key"
        self.demo_mode = False

    def search_poi_around(
        self,
        location,
        keywords=None,
        radius=500,
        city=None,
        page=1,
        offset=20,
        types=None,
    ):
        self.calls.append(
            {
                "location": location,
                "keywords": keywords,
                "types": types,
                "radius": radius,
                "city": city,
                "page": page,
                "offset": offset,
            }
        )
        return self.responses.pop(0)


def make_grids(district_count=3, grids_per_district=25):
    rows = []
    for district_index in range(district_count):
        district_name = f"测试区{district_index + 1}"
        adcode = f"52010{district_index + 1}"
        for grid_index in range(grids_per_district):
            rows.append(
                {
                    "grid_id": f"grid_{adcode}_{grid_index + 1:06d}",
                    "district_name": district_name,
                    "adcode": adcode,
                    "centroid_lon": 106.5 + district_index * 0.1 + grid_index * 0.005,
                    "centroid_lat": 26.4 + (grid_index % 5) * 0.01,
                    "area_km2": 1.0,
                    "geometry_wkt": "",
                    "data_source": "amap_boundary",
                }
            )
    return pd.DataFrame(rows)


class PoiFetcherTests(unittest.TestCase):
    def test_select_spatially_distributed_grids_is_stable_and_balanced(self):
        grids = make_grids()

        first = poi_fetcher.select_spatially_distributed_grids(grids, 20)
        second = poi_fetcher.select_spatially_distributed_grids(grids, 20)

        self.assertEqual(first["grid_id"].tolist(), second["grid_id"].tolist())
        self.assertEqual(first.groupby("district_name").size().to_dict(), {
            "测试区1": 20,
            "测试区2": 20,
            "测试区3": 20,
        })
        self.assertEqual(first["grid_id"].nunique(), 60)
        for _, district_rows in first.groupby("district_name"):
            self.assertGreater(
                district_rows["centroid_lon"].max() - district_rows["centroid_lon"].min(),
                0.08,
            )

    def test_fetch_category_stops_on_short_page_and_deduplicates_ids(self):
        first_page = [
            {
                "id": "poi-1",
                "name": "门店一",
                "type": "购物服务;便民商店/便利店",
                "location": "106.700000,26.500000",
                "address": "地址一",
            },
            {
                "id": "poi-1",
                "name": "门店一重复",
                "type": "购物服务;便民商店/便利店",
                "location": "106.700000,26.500000",
                "address": "地址一",
            },
            {
                "id": "",
                "name": "缺少标识门店",
                "type": "购物服务",
                "location": [],
                "address": [],
            },
        ]
        client = StubAmapClient([{"status": "1", "pois": first_page}])
        grid = make_grids(district_count=1, grids_per_district=1).iloc[0]

        rows, quality = poi_fetcher.fetch_grid_category(
            client=client,
            grid=grid,
            category_key="convenience_store",
            category_keyword="便利店",
            city_name="贵阳市",
            radius_m=500,
            max_pages=2,
            page_size=25,
        )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["poi_id"], "poi-1")
        self.assertEqual(rows[1]["poi_id"], "")
        self.assertEqual(rows[1]["lon"], "")
        self.assertEqual(rows[1]["lat"], "")
        self.assertEqual(quality["missing_location_count"], 1)

    def test_fetch_category_uses_second_page_and_keeps_cross_category_rows(self):
        page_one = [
            {
                "id": f"poi-{index}",
                "name": f"门店{index}",
                "type": "餐饮服务",
                "location": "106.700000,26.500000",
                "address": "测试地址",
            }
            for index in range(25)
        ]
        page_two = [
            {
                "id": "poi-0",
                "name": "跨页重复",
                "type": "餐饮服务",
                "location": "106.700000,26.500000",
                "address": "测试地址",
            },
            {
                "id": "poi-25",
                "name": "第二页门店",
                "type": "餐饮服务",
                "location": "106.710000,26.510000",
                "address": "测试地址二",
            },
        ]
        grid = make_grids(district_count=1, grids_per_district=1).iloc[0]
        client = StubAmapClient(
            [
                {"status": "1", "pois": page_one},
                {"status": "1", "pois": page_two},
                {"status": "1", "pois": [page_one[0]]},
            ]
        )

        restaurant_rows, _ = poi_fetcher.fetch_grid_category(
            client,
            grid,
            "restaurant",
            "餐饮",
            "贵阳市",
            500,
            2,
            25,
        )
        fast_food_rows, _ = poi_fetcher.fetch_grid_category(
            client,
            grid,
            "fast_food",
            "快餐",
            "贵阳市",
            500,
            2,
            25,
        )

        self.assertEqual(len(restaurant_rows), 26)
        self.assertEqual(len(fast_food_rows), 1)
        self.assertEqual(restaurant_rows[0]["poi_id"], fast_food_rows[0]["poi_id"])
        self.assertEqual([call["page"] for call in client.calls], [1, 2, 1])
        self.assertTrue(all(call["offset"] == 25 for call in client.calls))

    def test_fetch_category_retries_missing_response_only(self):
        client = StubAmapClient(
            [
                None,
                None,
                {
                    "status": "1",
                    "pois": [
                        {
                            "id": "poi-1",
                            "name": "重试后返回",
                            "type": "购物服务",
                            "location": "106.700000,26.500000",
                            "address": "测试地址",
                        }
                    ],
                },
            ]
        )
        grid = make_grids(district_count=1, grids_per_district=1).iloc[0]

        rows, quality = poi_fetcher.fetch_grid_category(
            client,
            grid,
            "convenience_store",
            "便利店",
            "贵阳市",
            500,
            2,
            25,
        )

        self.assertEqual(len(client.calls), 3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(quality["request_count"], 3)

    def test_build_count_rows_includes_zero_count_grids(self):
        grids = make_grids(district_count=1, grids_per_district=2)
        raw_rows = [
            {
                "grid_id": grids.iloc[0]["grid_id"],
                "district_name": grids.iloc[0]["district_name"],
                "category_key": "convenience_store",
                "category_keyword": "便利店",
                "poi_id": "poi-1",
                "poi_name": "门店一",
                "poi_type": "购物服务",
                "lon": 106.7,
                "lat": 26.5,
                "address": "地址一",
                "source": "amap_api",
            }
        ]

        counts = poi_fetcher.build_count_rows(grids, raw_rows, POI_CATEGORIES)

        self.assertEqual(len(counts), 2)
        self.assertEqual(counts[0]["convenience_store_count"], 1)
        self.assertEqual(counts[0]["supermarket_count"], 0)
        self.assertEqual(counts[1]["convenience_store_count"], 0)

    def test_write_outputs_uses_exact_schema(self):
        grids = make_grids(district_count=1, grids_per_district=1)
        raw_rows = [
            {
                "grid_id": grids.iloc[0]["grid_id"],
                "district_name": grids.iloc[0]["district_name"],
                "category_key": "convenience_store",
                "category_keyword": "便利店",
                "poi_id": "poi-1",
                "poi_name": "门店一",
                "poi_type": "购物服务",
                "lon": 106.7,
                "lat": 26.5,
                "address": "地址一",
                "source": "amap_api",
            }
        ]
        count_rows = poi_fetcher.build_count_rows(grids, raw_rows, POI_CATEGORIES)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "processed"
            report_path = Path(tmp_dir) / "results" / "poi_fetch_summary.md"
            paths = poi_fetcher.write_outputs_atomically(
                raw_rows=raw_rows,
                count_rows=count_rows,
                output_dir=output_dir,
                report_path=report_path,
                summary={
                    "total_grid_count": 790,
                    "fetched_grid_count": 1,
                    "district_grid_counts": {"测试区1": 1},
                    "category_counts": {"convenience_store": 1},
                    "category_keywords": POI_CATEGORIES,
                    "max_pages": 2,
                    "page_size": 25,
                    "radius_m": 500,
                    "missing_location_count": 0,
                    "request_count": 1,
                    "mode": "amap_api",
                },
            )
            with paths["raw"].open("r", encoding="utf-8-sig", newline="") as file:
                raw_header = next(csv.reader(file))
            with paths["counts"].open("r", encoding="utf-8-sig", newline="") as file:
                count_header = next(csv.reader(file))
            report = paths["report"].read_text(encoding="utf-8")

        self.assertEqual(raw_header, poi_fetcher.RAW_FIELDS)
        self.assertEqual(
            count_header,
            [
                "grid_id",
                "district_name",
                "convenience_store_count",
                "supermarket_count",
                "restaurant_count",
            ],
        )
        self.assertIn("实际采集网格数：1", report)
        self.assertIn("客户端查询调用次数（含缓存命中与重试）：1", report)
        self.assertIn("原型样本", report)
        self.assertIn("不代表全部 POI", report)

    def test_api_error_preserves_existing_outputs(self):
        grids = make_grids(district_count=1, grids_per_district=1)
        client = StubAmapClient(
            [{"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"}]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "processed"
            report_path = Path(tmp_dir) / "results" / "poi_fetch_summary.md"
            output_dir.mkdir(parents=True)
            report_path.parent.mkdir(parents=True)
            raw_path = output_dir / "grid_poi_raw.csv"
            counts_path = output_dir / "grid_poi_counts.csv"
            raw_path.write_text("existing raw", encoding="utf-8")
            counts_path.write_text("existing counts", encoding="utf-8")
            report_path.write_text("existing report", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "INVALID_USER_KEY.*10001"):
                poi_fetcher.run_api_fetch(
                    client=client,
                    grids=grids,
                    category_keywords={"convenience_store": "便利店"},
                    city_name="贵阳市",
                    radius_m=500,
                    max_pages=2,
                    page_size=25,
                    output_dir=output_dir,
                    report_path=report_path,
                    total_grid_count=790,
                )

            self.assertEqual(raw_path.read_text(encoding="utf-8"), "existing raw")
            self.assertEqual(counts_path.read_text(encoding="utf-8"), "existing counts")
            self.assertEqual(report_path.read_text(encoding="utf-8"), "existing report")

    def test_missing_key_requires_exact_demo_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            demo_path = Path(tmp_dir) / "grid_poi_counts_demo.csv"

            with self.assertRaisesRegex(
                FileNotFoundError,
                str(demo_path).replace("\\", "\\\\"),
            ):
                poi_fetcher.load_demo_counts(demo_path)

    def test_select_typecode_comparison_grids_uses_largest_zero_and_median_nonzero(self):
        grids = make_grids(district_count=3, grids_per_district=4)
        grids.loc[grids["grid_id"].str.endswith("000001"), "area_km2"] = 0.2
        grids.loc[grids["grid_id"].str.endswith("000002"), "area_km2"] = 0.9
        rows = []
        for district_index in range(3):
            adcode = f"52010{district_index + 1}"
            totals = [0, 0, 4, 10]
            for grid_index, total in enumerate(totals, start=1):
                rows.append(
                    {
                        "grid_id": f"grid_{adcode}_{grid_index:06d}",
                        "district_name": f"测试区{district_index + 1}",
                        "convenience_store_count": total,
                        "supermarket_count": 0,
                    }
                )
        counts = pd.DataFrame(rows)

        selected = poi_fetcher.select_typecode_comparison_grids(
            grids,
            counts,
            ["测试区1", "测试区2", "测试区3"],
        )

        self.assertEqual(len(selected), 6)
        self.assertEqual(
            selected.groupby(["district_name", "sample_group"]).size().to_dict(),
            {
                ("测试区1", "nonzero"): 1,
                ("测试区1", "zero"): 1,
                ("测试区2", "nonzero"): 1,
                ("测试区2", "zero"): 1,
                ("测试区3", "nonzero"): 1,
                ("测试区3", "zero"): 1,
            },
        )
        self.assertTrue(
            selected[selected["sample_group"] == "zero"]["grid_id"].str.endswith("000002").all()
        )
        self.assertTrue(
            selected[selected["sample_group"] == "nonzero"]["grid_id"].str.endswith("000004").all()
        )

    def test_evaluate_typecode_comparison_applies_both_thresholds(self):
        converted_rows = [
            {
                "grid_id": "zero-grid",
                "sample_group": "zero",
                "keyword_count": 0,
                "typecode_count": 1,
            },
            {
                "grid_id": "nonzero-grid",
                "sample_group": "nonzero",
                "keyword_count": 10,
                "typecode_count": 10,
            },
        ]
        increase_rows = [
            {
                "grid_id": "zero-grid",
                "sample_group": "zero",
                "keyword_count": 0,
                "typecode_count": 0,
            },
            {
                "grid_id": "nonzero-grid",
                "sample_group": "nonzero",
                "keyword_count": 10,
                "typecode_count": 13,
            },
        ]
        unchanged_rows = [
            {
                "grid_id": "zero-grid",
                "sample_group": "zero",
                "keyword_count": 0,
                "typecode_count": 0,
            },
            {
                "grid_id": "nonzero-grid",
                "sample_group": "nonzero",
                "keyword_count": 10,
                "typecode_count": 11,
            },
        ]

        converted = poi_fetcher.evaluate_typecode_comparison(converted_rows)
        increased = poi_fetcher.evaluate_typecode_comparison(increase_rows)
        unchanged = poi_fetcher.evaluate_typecode_comparison(unchanged_rows)

        self.assertTrue(converted["recommend_full_refetch"])
        self.assertEqual(converted["converted_zero_grid_count"], 1)
        self.assertTrue(increased["recommend_full_refetch"])
        self.assertAlmostEqual(increased["increase_ratio"], 0.3)
        self.assertFalse(unchanged["recommend_full_refetch"])

    def test_run_typecode_comparison_writes_only_independent_outputs(self):
        grids = make_grids(district_count=1, grids_per_district=2)
        grids["sample_group"] = ["zero", "nonzero"]
        counts = pd.DataFrame(
            [
                {
                    "grid_id": grids.iloc[0]["grid_id"],
                    "district_name": grids.iloc[0]["district_name"],
                    "convenience_store_count": 0,
                },
                {
                    "grid_id": grids.iloc[1]["grid_id"],
                    "district_name": grids.iloc[1]["district_name"],
                    "convenience_store_count": 2,
                },
            ]
        )
        client = StubAmapClient(
            [
                {"status": "1", "pois": []},
                {
                    "status": "1",
                    "pois": [
                        {
                            "id": "poi-1",
                            "name": "分类编码门店",
                            "type": "购物服务",
                            "location": "106.700000,26.500000",
                            "address": "测试地址",
                        }
                    ],
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            processed_dir = base / "processed"
            results_dir = base / "results"
            processed_dir.mkdir()
            raw_path = processed_dir / "grid_poi_raw.csv"
            counts_path = processed_dir / "grid_poi_counts.csv"
            raw_path.write_text("existing raw", encoding="utf-8")
            counts_path.write_text("existing counts", encoding="utf-8")

            outputs = poi_fetcher.run_typecode_comparison(
                client=client,
                selected_grids=grids,
                existing_counts=counts,
                category_keywords={"convenience_store": "便利店"},
                category_typecodes={"convenience_store": "060200"},
                city_name="贵阳市",
                radius_m=500,
                max_pages=2,
                page_size=25,
                results_dir=results_dir,
            )

            comparison = pd.read_csv(outputs["csv"])
            report = outputs["report"].read_text(encoding="utf-8")
            self.assertEqual(raw_path.read_text(encoding="utf-8"), "existing raw")
            self.assertEqual(counts_path.read_text(encoding="utf-8"), "existing counts")

        self.assertEqual(len(comparison), 2)
        self.assertEqual(
            comparison.columns.tolist(),
            poi_fetcher.COMPARISON_FIELDS,
        )
        self.assertIn("是否建议重新采集60个网格", report)
        self.assertTrue(all(call["keywords"] is None for call in client.calls))
        self.assertTrue(all(call["types"] == "060200" for call in client.calls))


if __name__ == "__main__":
    unittest.main()
