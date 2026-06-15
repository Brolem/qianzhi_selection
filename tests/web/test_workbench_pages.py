import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import pandas as pd

from src.web.pages.common import (
    load_required_csv,
    profile_top_rows,
)
from src.web.pages.data_foundation import (
    build_data_foundation_rows,
    format_data_foundation_table,
)
from src.web.pages.district_compare import (
    format_district_summary_table,
    load_district_comparison,
)
from src.web.pages.district_compare import (
    _grouped_bar_chart,
    build_district_poi_comparison,
)
from src.web.pages.grid_recommendation import (
    _metric_chart,
    _diagnostic_summary_html,
    _render_selected_grid_detail,
    _weight_budget_html,
    detail_grid_labels,
    diagnostic_summary_counts,
    metric_breakdown_data,
    ranked_recommendation_rows,
)
from src.web.pages.overview import (
    _coverage_funnel_html,
    _poi_theme_chart,
    _score_average_chart,
    build_coverage_funnel_data,
    build_poi_theme_summary_data,
    build_score_average_data,
    build_score_distribution_data,
    load_overview_metrics,
)


class ProfileSpec:
    profile_id = "test_profile"
    profile_name = "测试方案"
    score_field = "profile_score"
    rank_field = "profile_rank"
    district_rank_field = "district_profile_rank"
    advantage_field = "profile_main_advantage"
    risk_field = "profile_main_risk"
    level_field = "profile_recommendation_level"
    synergy_field = "convenience_synergy_score"
    competition_pressure_field = "convenience_competition_pressure"
    demand_proxy_field = "profile_demand_customer_proxy"
    market_stage_field = "profile_market_stage"
    competition_alert_field = "profile_competition_alert"
    diagnosis_summary_field = "profile_diagnosis_summary"

    def __init__(self, result_path):
        self.result_path = result_path


def write_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


class WorkbenchPageTests(unittest.TestCase):
    def test_coverage_funnel_uses_spatial_sample_and_active_counts(self):
        stages = build_coverage_funnel_data(
            {
                "spatial_grid_count": 790,
                "poi_sample_grid_count": 60,
                "active_grid_count": 41,
            }
        )
        content = _coverage_funnel_html(stages)

        self.assertEqual(
            stages[["stage", "count"]].to_dict("records"),
            [
                {"stage": "空间评价网格", "count": 790},
                {"stage": "已采集样本网格", "count": 60},
                {"stage": "活跃评分网格", "count": 41},
            ],
        )
        self.assertAlmostEqual(stages.iloc[1]["rate_from_previous"], 60 / 790)
        self.assertAlmostEqual(stages.iloc[2]["rate_from_previous"], 41 / 60)
        self.assertIn("790", content)
        self.assertIn("60", content)
        self.assertIn("41", content)
        self.assertIn("7.6%", content)
        self.assertIn("68.3%", content)

    def test_weight_budget_html_uses_progress_and_compact_status_items(self):
        content = _weight_budget_html(
            total=Decimal("96.00"),
            remaining=Decimal("4.00"),
        )

        self.assertIn("workbench-budget-progress", content)
        self.assertIn("width:96.00%", content)
        self.assertIn("已分配", content)
        self.assertIn("96.00%", content)
        self.assertIn("剩余", content)
        self.assertIn("4.00%", content)
        self.assertIn("仅预览", content)

    def test_diagnostic_summary_html_uses_five_semantic_compact_cards(self):
        content = _diagnostic_summary_html(
            {
                "市场空白型": 1,
                "待培育型": 12,
                "成熟商圈型": 12,
                "一般观察型": 16,
                "过度竞争预警": 12,
            }
        )

        self.assertEqual(content.count("workbench-diagnostic-card "), 5)
        for class_name in [
            "is-gap",
            "is-cultivation",
            "is-mature",
            "is-general",
            "is-alert",
        ]:
            self.assertIn(class_name, content)
        self.assertIn("市场空白型", content)
        self.assertIn(">1<", content)

    def test_load_required_csv_reports_exact_missing_path_and_field(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            missing = base / "missing.csv"
            with self.assertRaisesRegex(FileNotFoundError, str(missing).replace("\\", "\\\\")):
                load_required_csv(missing, ["grid_id"])

            table = write_csv(base / "table.csv", [{"grid_id": "grid_1"}])
            with self.assertRaisesRegex(KeyError, "district_name"):
                load_required_csv(table, ["grid_id", "district_name"])

    def test_load_overview_metrics_uses_real_v2_scope_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            districts = write_csv(
                base / "districts.csv",
                [{"district_name": "甲区"}, {"district_name": "乙区"}],
            )
            grids = write_csv(
                base / "grids.csv",
                [{"grid_id": "g1"}, {"grid_id": "g2"}, {"grid_id": "g3"}],
            )
            poi_counts = write_csv(
                base / "poi.csv",
                [{"grid_id": "g1"}, {"grid_id": "g2"}],
            )
            scores = write_csv(
                base / "scores.csv",
                [
                    {"grid_id": "g1", "has_poi_activity": True},
                    {"grid_id": "g2", "has_poi_activity": False},
                ],
            )

            result = load_overview_metrics(
                districts_path=districts,
                grids_path=grids,
                poi_counts_path=poi_counts,
                scores_path=scores,
                profile_specs={"默认": object(), "自定义": object()},
                poi_categories={
                    "convenience_store": "便利店",
                    "restaurant": "餐饮",
                },
            )

            self.assertEqual(
                result,
                {
                    "district_count": 2,
                    "spatial_grid_count": 3,
                    "poi_sample_grid_count": 2,
                    "poi_category_count": 2,
                    "active_grid_count": 1,
                    "profile_count": 2,
                },
            )

    def test_build_data_foundation_rows_uses_exact_files_and_roles(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            districts = write_csv(
                base / "target_districts.csv",
                [
                    {
                        "district_name": "甲区",
                        "adcode": "520101",
                        "data_source": "amap_api",
                    }
                ],
            )
            poi_counts = write_csv(
                base / "grid_poi_counts.csv",
                [{"grid_id": "g1", "district_name": "甲区"}],
            )
            macro = write_csv(
                base / "macro_clean.csv",
                [
                    {
                        "area_code": "520000",
                        "index_name": "测试指标",
                        "value": 1,
                    }
                ],
            )
            employment = write_csv(
                base / "employment_clean.csv",
                [{"region_id": "520000", "region_name": "贵州省"}],
            )

            rows = build_data_foundation_rows(
                districts_path=districts,
                poi_counts_path=poi_counts,
                macro_path=macro,
                employment_path=employment,
            )

            self.assertEqual([row["record_count"] for row in rows], [1, 1, 1, 1])
            self.assertEqual(rows[0]["data_role"], "区县边界与空间约束")
            self.assertNotIn("file_path", rows[0])
            self.assertEqual(rows[1]["geographic_scope"], "贵阳市三个目标区县的 60 个样本网格")
            self.assertEqual(rows[2]["geographic_scope"], "贵州省级背景")
            self.assertEqual(rows[3]["geographic_scope"], "贵州省级背景")

            display = format_data_foundation_table(rows)
            self.assertEqual(
                display.columns.tolist(),
                ["数据资产", "记录数", "地域范围", "数据角色", "坐标与口径"],
            )
            self.assertEqual(display.iloc[0]["数据资产"], "目标区县基础信息")

    def test_profile_top_rows_filters_activity_district_and_rank(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_csv(
                Path(tmp_dir) / "scores.csv",
                [
                    {
                        "grid_id": "g3",
                        "district_name": "乙区",
                        "has_poi_activity": True,
                        "profile_score": 70,
                        "profile_rank": 3,
                    },
                    {
                        "grid_id": "g1",
                        "district_name": "甲区",
                        "has_poi_activity": True,
                        "profile_score": 90,
                        "profile_rank": 1,
                    },
                    {
                        "grid_id": "g2",
                        "district_name": "甲区",
                        "has_poi_activity": False,
                        "profile_score": 0,
                        "profile_rank": None,
                    },
                ],
            )
            spec = ProfileSpec(result_path)

            all_rows = profile_top_rows(spec, limit=5)
            district_rows = profile_top_rows(spec, district_name="甲区", limit=10)

            self.assertEqual(all_rows["grid_id"].tolist(), ["g1", "g3"])
            self.assertEqual(district_rows["grid_id"].tolist(), ["g1"])

    def test_load_district_comparison_requires_step8_summary_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_csv(
                Path(tmp_dir) / "district_summary.csv",
                [
                    {
                        "district_name": "甲区",
                        "grid_count": 20,
                        "active_grid_count": 12,
                        "poi_total_count": 100,
                        "avg_convenience_score": 50,
                        "top_convenience_grid_id": "g1",
                        "avg_light_food_score": 48,
                        "top_light_food_grid_id": "g2",
                    }
                ],
            )

            result = load_district_comparison(path)

            self.assertEqual(result["district_name"].tolist(), ["甲区"])
            self.assertEqual(result["active_grid_count"].tolist(), [12])
            display = format_district_summary_table(result)
            self.assertEqual(
                display.columns.tolist(),
                [
                    "区县",
                    "网格数",
                    "活跃网格数",
                    "POI 总量",
                    "便利店平均分",
                    "便利店最高分网格",
                    "轻餐饮平均分",
                    "轻餐饮最高分网格",
                ],
            )
            self.assertEqual(display.iloc[0]["便利店平均分"], 50.0)

    def test_overview_chart_data_uses_exact_themes_and_active_scores(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            poi_path = write_csv(
                base / "poi.csv",
                [
                    {
                        "district_name": "甲区",
                        "convenience_store_count": 2,
                        "supermarket_count": 1,
                        "restaurant_count": 3,
                        "fast_food_count": 4,
                        "snack_count": 5,
                        "cafe_count": 6,
                        "tea_count": 7,
                        "school_count": 8,
                        "hospital_count": 9,
                        "residential_count": 10,
                        "mall_count": 11,
                        "office_count": 12,
                        "bus_stop_count": 13,
                        "subway_station_count": 14,
                        "parking_count": 15,
                    },
                    {
                        "district_name": "甲区",
                        "convenience_store_count": 5,
                        "supermarket_count": 10,
                        "restaurant_count": 7,
                        "fast_food_count": 0,
                        "snack_count": 0,
                        "cafe_count": 0,
                        "tea_count": 0,
                        "school_count": 0,
                        "hospital_count": 0,
                        "residential_count": 0,
                        "mall_count": 0,
                        "office_count": 0,
                        "bus_stop_count": 0,
                        "subway_station_count": 0,
                        "parking_count": 0,
                    },
                    {
                        "district_name": "乙区",
                        "convenience_store_count": 11,
                        "supermarket_count": 0,
                        "restaurant_count": 13,
                        "fast_food_count": 0,
                        "snack_count": 0,
                        "cafe_count": 0,
                        "tea_count": 0,
                        "school_count": 0,
                        "hospital_count": 0,
                        "residential_count": 0,
                        "mall_count": 0,
                        "office_count": 0,
                        "bus_stop_count": 0,
                        "subway_station_count": 0,
                        "parking_count": 0,
                    },
                ],
            )
            score_path = write_csv(
                base / "scores.csv",
                [
                    {
                        "district_name": "甲区",
                        "has_poi_activity": True,
                        "convenience_score": 80,
                        "light_food_score": 70,
                    },
                    {
                        "district_name": "乙区",
                        "has_poi_activity": False,
                        "convenience_score": 0,
                        "light_food_score": 0,
                    },
                ],
            )
            summary = build_poi_theme_summary_data(poi_path)
            distribution = build_score_distribution_data(score_path)
            averages = build_score_average_data(score_path)

            self.assertEqual(
                summary.loc[
                    summary["district_name"].eq("甲区")
                    & summary["poi_theme"].eq("community_retail"),
                    "poi_count",
                ].tolist(),
                [18],
            )
            self.assertEqual(
                summary["theme_label"].drop_duplicates().tolist(),
                ["社区零售", "餐饮消费", "生活客群", "商业办公", "交通配套"],
            )
            self.assertEqual(len(summary), 10)
            self.assertEqual(len(distribution), 2)
            self.assertEqual(
                sorted(distribution["profile_name"].unique()),
                ["社区便利店", "轻餐饮"],
            )
            self.assertNotIn(0, distribution["score"].tolist())
            self.assertEqual(averages["active_grid_count"].tolist(), [1, 1])
            self.assertEqual(averages["average_score"].tolist(), [80.0, 70.0])

            theme_chart_spec = _poi_theme_chart(summary).to_dict()
            self.assertIsNone(
                theme_chart_spec["encoding"]["color"]["legend"],
            )
            self.assertIsNone(
                theme_chart_spec["encoding"]["color"]["title"],
            )

            chart_spec = _score_average_chart(averages).to_dict()
            x_encoding = chart_spec["layer"][0]["encoding"]["x"]
            self.assertEqual(x_encoding["scale"]["domain"], [20, 40])
            self.assertEqual(
                x_encoding["axis"]["values"],
                [20, 25, 30, 35, 40],
            )
            self.assertEqual(chart_spec["layer"][0]["mark"]["type"], "bar")
            self.assertEqual(
                chart_spec["layer"][0]["encoding"]["yOffset"]["field"],
                "profile_name",
            )
            self.assertEqual(chart_spec["layer"][1]["mark"]["type"], "text")
            self.assertEqual(
                chart_spec["layer"][1]["encoding"]["yOffset"]["field"],
                "profile_name",
            )
            self.assertIsNone(
                chart_spec["layer"][0]["encoding"]["color"]["legend"],
            )
            self.assertEqual(theme_chart_spec["height"], chart_spec["height"])
            self.assertEqual(theme_chart_spec["height"], 255)

    def test_district_poi_comparison_uses_raw_grouped_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            poi_path = write_csv(
                Path(tmp_dir) / "poi.csv",
                [
                    {
                        "district_name": "甲区",
                        "convenience_store_count": 2,
                        "restaurant_count": 3,
                        "school_count": 4,
                        "hospital_count": 5,
                        "mall_count": 6,
                        "office_count": 7,
                        "residential_count": 8,
                        "bus_stop_count": 9,
                        "subway_station_count": 10,
                        "parking_count": 11,
                    },
                    {
                        "district_name": "甲区",
                        "convenience_store_count": 20,
                        "restaurant_count": 30,
                        "school_count": 40,
                        "hospital_count": 50,
                        "mall_count": 60,
                        "office_count": 70,
                        "residential_count": 80,
                        "bus_stop_count": 90,
                        "subway_station_count": 100,
                        "parking_count": 110,
                    },
                ],
            )

            result = build_district_poi_comparison(poi_path)

            self.assertEqual(
                result.loc[
                    result["poi_category"].eq("convenience_store"),
                    "poi_count",
                ].tolist(),
                [22],
            )
            self.assertEqual(
                sorted(result["category_group"].unique()),
                ["主力业态", "交通设施", "客群与商业设施"],
            )

            chart_spec = _grouped_bar_chart(result, "主力业态").to_dict()
            x_axis = chart_spec["encoding"]["x"]["axis"]
            self.assertEqual(x_axis["labelAngle"], 360)
            self.assertEqual(x_axis["labelPadding"], 8)
            self.assertEqual(chart_spec["height"], 230)
            self.assertEqual(
                chart_spec["encoding"]["color"]["legend"]["orient"],
                "top",
            )

            facility_spec = _grouped_bar_chart(
                result,
                "客群与商业设施",
                show_legend=False,
                height=260,
            ).to_dict()
            self.assertEqual(facility_spec["height"], 260)
            self.assertIsNone(
                facility_spec["encoding"]["color"]["legend"],
            )

    def test_recommendation_rows_use_active_global_or_district_rank(self):
        frame = pd.DataFrame(
            [
                {
                    "grid_id": "g3",
                    "district_name": "乙区",
                    "has_poi_activity": True,
                    "profile_rank": 3,
                    "district_profile_rank": 1,
                },
                {
                    "grid_id": "g1",
                    "district_name": "甲区",
                    "has_poi_activity": True,
                    "profile_rank": 1,
                    "district_profile_rank": 2,
                },
                {
                    "grid_id": "g2",
                    "district_name": "甲区",
                    "has_poi_activity": True,
                    "profile_rank": 2,
                    "district_profile_rank": 1,
                },
                {
                    "grid_id": "g4",
                    "district_name": "甲区",
                    "has_poi_activity": False,
                    "profile_rank": None,
                    "district_profile_rank": None,
                },
            ]
        )

        global_rows = ranked_recommendation_rows(
            frame,
            rank_field="profile_rank",
            district_rank_field="district_profile_rank",
            district_name="全部",
            limit=10,
        )
        district_rows = ranked_recommendation_rows(
            frame,
            rank_field="profile_rank",
            district_rank_field="district_profile_rank",
            district_name="甲区",
            limit=5,
        )

        self.assertEqual(global_rows["grid_id"].tolist(), ["g1", "g2", "g3"])
        self.assertEqual(district_rows["grid_id"].tolist(), ["g2", "g1"])

    def test_diagnostic_filters_return_all_matches_in_original_rank_order(self):
        frame = pd.DataFrame(
            [
                {
                    "grid_id": "g1",
                    "district_name": "甲区",
                    "has_poi_activity": True,
                    "profile_rank": 1,
                    "district_profile_rank": 1,
                    "profile_market_stage": "成熟商圈型",
                    "profile_competition_alert": "过度竞争预警",
                },
                {
                    "grid_id": "g2",
                    "district_name": "甲区",
                    "has_poi_activity": True,
                    "profile_rank": 2,
                    "district_profile_rank": 2,
                    "profile_market_stage": "成熟商圈型",
                    "profile_competition_alert": "未触发过度竞争预警",
                },
                {
                    "grid_id": "g3",
                    "district_name": "乙区",
                    "has_poi_activity": True,
                    "profile_rank": 3,
                    "district_profile_rank": 1,
                    "profile_market_stage": "市场空白型",
                    "profile_competition_alert": "未触发过度竞争预警",
                },
            ]
        )

        rows = ranked_recommendation_rows(
            frame,
            rank_field="profile_rank",
            district_rank_field="district_profile_rank",
            district_name="全部",
            limit=None,
            market_stage_field="profile_market_stage",
            competition_alert_field="profile_competition_alert",
            market_stage="成熟商圈型",
            competition_alert="过度竞争预警",
        )
        summary = diagnostic_summary_counts(
            frame,
            market_stage_field="profile_market_stage",
            competition_alert_field="profile_competition_alert",
        )

        self.assertEqual(rows["grid_id"].tolist(), ["g1"])
        self.assertEqual(summary["成熟商圈型"], 2)
        self.assertEqual(summary["市场空白型"], 1)
        self.assertEqual(summary["过度竞争预警"], 1)

    def test_detail_options_follow_the_current_diagnostic_result_rows(self):
        rows = pd.DataFrame(
            [
                {
                    "grid_id": "gap_grid",
                    "district_name": "甲区",
                    "profile_rank": 9,
                    "profile_score": 52.5,
                }
            ]
        )
        view = type(
            "View",
            (),
            {
                "rank_field": "profile_rank",
                "score_field": "profile_score",
            },
        )()

        labels = detail_grid_labels(rows, view)

        self.assertEqual(list(labels), ["gap_grid"])
        self.assertIn("全局第 9 名", labels["gap_grid"])

    def test_metric_breakdown_uses_positive_competition_score(self):
        row = pd.Series(
            {
                "traffic_accessibility": 10,
                "consumption_potential": 20,
                "employment_customer_proxy": 30,
                "convenience_synergy_score": 40,
                "profile_competition_score": 80,
                "business_atmosphere": 60,
            }
        )

        result = metric_breakdown_data(
            row,
            synergy_field="convenience_synergy_score",
            competition_score_field="profile_competition_score",
        )

        self.assertEqual(result["metric_name"].tolist()[4], "低竞争得分")
        self.assertEqual(result["metric_value"].tolist(), [10, 20, 30, 40, 80, 60])

    def test_selected_grid_detail_uses_compact_summary_and_chart_columns(self):
        class Context:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        class FakeStreamlit:
            def __init__(self):
                self.column_specs = []
                self.html_calls = []
                self.markdown_calls = []
                self.chart_count = 0

            def columns(self, spec, gap):
                self.column_specs.append((spec, gap))
                return Context(), Context()

            def container(self, border):
                self.border = border
                return Context()

            def html(self, value):
                self.html_calls.append(value)

            def markdown(self, value, **kwargs):
                self.markdown_calls.append((value, kwargs))

            def altair_chart(self, chart, width):
                self.chart_count += 1
                self.chart_width = width

        view = type(
            "View",
            (),
            {
                "score_field": "profile_score",
                "rank_field": "profile_rank",
                "level_field": "profile_recommendation_level",
                "synergy_field": "convenience_synergy_score",
                "competition_score_field": "profile_competition_score",
                "market_stage_field": "profile_market_stage",
                "competition_alert_field": "profile_competition_alert",
            },
        )()
        selected = pd.Series(
            {
                "profile_score": 83.03,
                "profile_rank": 1,
                "profile_recommendation_level": "推荐",
                "traffic_accessibility": 100,
                "consumption_potential": 96,
                "employment_customer_proxy": 99,
                "convenience_synergy_score": 96,
                "profile_competition_score": 0,
                "business_atmosphere": 99,
                "profile_market_stage": "成熟商圈型",
                "profile_competition_alert": "过度竞争预警",
            }
        )
        st = FakeStreamlit()

        _render_selected_grid_detail(st, selected, view)

        self.assertEqual(st.column_specs, [([1, 2.4], "large")])
        self.assertEqual(len(st.html_calls), 1)
        self.assertIn("83.03", st.html_calls[0])
        self.assertIn("全局 #1", st.html_calls[0])
        self.assertIn("推荐", st.html_calls[0])
        self.assertIn("成熟商圈型", st.html_calls[0])
        self.assertIn("过度竞争预警", st.html_calls[0])
        self.assertEqual(st.chart_count, 1)

        chart_spec = _metric_chart(
            metric_breakdown_data(
                selected,
                synergy_field=view.synergy_field,
                competition_score_field=view.competition_score_field,
            )
        ).to_dict()
        self.assertEqual(len(chart_spec["layer"]), 3)
        self.assertEqual(chart_spec["layer"][0]["mark"]["color"], "#E7ECEA")
        self.assertEqual(chart_spec["layer"][2]["mark"]["type"], "text")


if __name__ == "__main__":
    unittest.main()
