import tempfile
import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from src.app import (
    PAGE_REGISTRATIONS,
    render_map_page,
    render_report_page,
    run_workbench,
    run_navigation,
)
from src.presentation.report_generator import ReportGenerationResult
from src.presentation.map_viz import MapProfileSpec
from src.web.pages.grid_recommendation import render as render_grid_recommendation_page
from src.web.pages.report_center import (
    _report_preview_html,
    build_report_preview,
)


class FakeStreamlit:
    def __init__(
        self,
        selected_label=None,
        clicked_buttons=None,
        session_state=None,
        toggle_value=False,
    ):
        self.selected_label = selected_label
        self.clicked_buttons = set(clicked_buttons or [])
        self.session_state = session_state if session_state is not None else {}
        self.headers = []
        self.errors = []
        self.warnings = []
        self.infos = []
        self.markdowns = []
        self.downloads = []
        self.selectboxes = {}
        self.column_calls = []
        self.subheaders = []
        self.captions = []
        self.toggle_value = toggle_value
        self.toggle_calls = []
        self.status_calls = []
        self.status_updates = []
        self.container_calls = []
        self.html_calls = []
        self.chart_calls = []
        self.link_button_calls = []
        self.dataframe_calls = []
        self.successes = []

    def header(self, text):
        self.headers.append(text)

    def success(self, text):
        self.successes.append(text)

    def selectbox(self, label, options, index=0, key=None, format_func=None):
        del key, format_func
        options = list(options)
        self.selectboxes[label] = options
        self.selectbox_label = label
        self.selectbox_options = options
        self.selectbox_index = index
        if isinstance(self.selected_label, dict):
            selected = self.selected_label.get(label, options[index])
            return selected if selected in options else options[index]
        if self.selected_label is None:
            return options[index]
        return self.selected_label if self.selected_label in options else options[index]

    def error(self, text):
        self.errors.append(text)

    def warning(self, text):
        self.warnings.append(text)

    def info(self, text):
        self.infos.append(text)

    def markdown(self, text):
        self.markdowns.append(text)

    def html(self, text):
        self.html_calls.append(text)

    def altair_chart(self, chart, **kwargs):
        self.chart_calls.append((chart, kwargs))

    def dataframe(self, frame, **kwargs):
        self.dataframe_calls.append((frame.copy(), kwargs))

    def subheader(self, text):
        self.subheaders.append(text)

    def caption(self, text):
        self.captions.append(text)

    def columns(self, spec, gap=None):
        self.column_calls.append((spec, gap))
        count = spec if isinstance(spec, int) else len(spec)
        return [FakeContext() for _ in range(count)]

    def container(self, border=False, key=None):
        self.container_calls.append(
            {
                "border": border,
                "key": key,
            }
        )
        return FakeContext()

    def button(self, label):
        return label in self.clicked_buttons

    def link_button(self, label, url, **kwargs):
        self.link_button_calls.append((label, url, kwargs))
        return False

    def download_button(self, label, **kwargs):
        self.downloads.append((label, kwargs))

    def toggle(self, label, value=False):
        self.toggle_calls.append((label, value))
        return self.toggle_value

    def status(
        self,
        label,
        *,
        expanded=False,
        state="running",
        type="default",
        width="stretch",
    ):
        self.status_calls.append(
            {
                "label": label,
                "expanded": expanded,
                "state": state,
                "type": type,
                "width": width,
            }
        )
        return FakeStatus(self.status_updates)


class FakeComponents:
    def __init__(self):
        self.calls = []

    def html(self, content, height, scrolling):
        self.calls.append(
            {
                "content": content,
                "height": height,
                "scrolling": scrolling,
            }
        )


class FakeContext:
    def info(self, text):
        self.info_text = text

    def warning(self, text):
        self.warning_text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeStatus(FakeContext):
    def __init__(self, updates):
        self.updates = updates

    def update(self, **kwargs):
        self.updates.append(kwargs)


class FakeNavigationPage:
    def __init__(self, renderer, *, title, url_path, default=False):
        self.renderer = renderer
        self.title = title
        self.url_path = url_path
        self.default = default


class FakeNavigationController:
    def __init__(self):
        self.run_count = 0

    def run(self):
        self.run_count += 1


class FakeSidebar:
    def __init__(self, selected):
        self.selected = selected
        self.radio_calls = []

    def radio(self, label, options):
        values = list(options)
        self.radio_calls.append((label, values))
        return self.selected


class FakeNavigationStreamlit:
    def __init__(self, *, selected_fallback=None, supports_navigation=True):
        self.created_pages = []
        self.navigation_calls = []
        self.controller = FakeNavigationController()
        self.sidebar = FakeSidebar(selected_fallback)
        self.page_config_calls = []
        self.html_calls = []
        if supports_navigation:
            self.Page = self._page
            self.navigation = self._navigation

    def set_page_config(self, **kwargs):
        self.page_config_calls.append(kwargs)

    def html(self, body):
        self.html_calls.append(body)

    def _page(self, renderer, *, title, url_path, default=False):
        page = FakeNavigationPage(
            renderer,
            title=title,
            url_path=url_path,
            default=default,
        )
        self.created_pages.append(page)
        return page

    def _navigation(self, pages, *, position, expanded):
        self.navigation_calls.append(
            {
                "pages": list(pages),
                "position": position,
                "expanded": expanded,
            }
        )
        return self.controller


def make_map_spec(
    profile_id: str,
    profile_name: str,
    result_path: Path,
    static_html_path: Path | None,
) -> MapProfileSpec:
    return MapProfileSpec(
        profile_id=profile_id,
        profile_name=profile_name,
        template_id="community_retail",
        weights={
            "traffic_accessibility": 0.20,
            "consumption_potential": 0.25,
            "employment_customer_proxy": 0.10,
            "synergy_score": 0.20,
            "competition_pressure": 0.15,
            "business_atmosphere": 0.10,
        },
        result_path=result_path,
        metadata_path=result_path.parent / "profile_metadata.json",
        static_html_path=static_html_path,
        score_field="profile_score",
        rank_field="profile_rank",
        district_rank_field="district_profile_rank",
        competition_score_field="profile_competition_score",
        competition_pressure_field="convenience_competition_pressure",
        advantage_field="profile_main_advantage",
        risk_field="profile_main_risk",
        level_field="profile_recommendation_level",
        synergy_field="convenience_synergy_score",
        demand_proxy_field="profile_demand_customer_proxy",
        market_stage_field="profile_market_stage",
        competition_alert_field="profile_competition_alert",
        diagnosis_summary_field="profile_diagnosis_summary",
    )


def write_report_result(path: Path) -> Path:
    rows = []
    for index in range(60):
        active = index < 41
        rows.append(
            {
                "grid_id": f"grid_{index + 1:03d}",
                "district_name": "测试区",
                "centroid_lon": 106.7,
                "centroid_lat": 26.6,
                "area_km2": 1.0,
                "poi_total_count": 10 if active else 0,
                "poi_category_coverage": 5 if active else 0,
                "has_poi_activity": active,
                "traffic_accessibility": 50.0,
                "consumption_potential": 50.0,
                "employment_customer_proxy": 50.0,
                "business_atmosphere": 50.0,
                "convenience_synergy_score": 50.0,
                "convenience_competition_pressure": 50.0,
                "convenience_competition_score": 50.0,
                "convenience_score": 100.0 - index if active else 0.0,
                "convenience_rank": index + 1 if active else None,
                "convenience_district_rank": index + 1 if active else None,
                "convenience_main_advantage": "交通可达性",
                "convenience_main_risk": "消费潜力不足",
                "convenience_recommendation_level": "推荐" if index < 9 else "暂不推荐",
                "convenience_demand_customer_proxy": 50.0 if active else 0.0,
                "convenience_market_stage": "一般观察型" if active else "无 POI 活动",
                "convenience_competition_alert": (
                    "未触发过度竞争预警" if active else "不参与诊断"
                ),
                "convenience_diagnosis_summary": (
                    "一般观察型；未触发过度竞争预警。"
                    if active
                    else "无 POI 活动，不参与区域市场诊断。"
                ),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def make_report_spec(result_path: Path) -> MapProfileSpec:
    return MapProfileSpec(
        profile_id="convenience",
        profile_name="社区便利店",
        template_id="community_retail",
        weights={
            "traffic_accessibility": 0.20,
            "consumption_potential": 0.25,
            "employment_customer_proxy": 0.10,
            "synergy_score": 0.20,
            "competition_pressure": 0.15,
            "business_atmosphere": 0.10,
        },
        result_path=result_path,
        metadata_path=result_path.parent / "profile_metadata.json",
        static_html_path=None,
        score_field="convenience_score",
        rank_field="convenience_rank",
        district_rank_field="convenience_district_rank",
        competition_score_field="convenience_competition_score",
        competition_pressure_field="convenience_competition_pressure",
        advantage_field="convenience_main_advantage",
        risk_field="convenience_main_risk",
        level_field="convenience_recommendation_level",
        synergy_field="convenience_synergy_score",
        demand_proxy_field="convenience_demand_customer_proxy",
        market_stage_field="convenience_market_stage",
        competition_alert_field="convenience_competition_alert",
        diagnosis_summary_field="convenience_diagnosis_summary",
    )


class AppHelperTests(unittest.TestCase):
    def test_report_preview_uses_selected_grid_score_diagnosis_and_six_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = write_report_result(base / "result.csv")
            spec = make_report_spec(result_path)
            frame = pd.read_csv(result_path)

            preview = build_report_preview(
                frame,
                spec,
                "grid_001",
            )
            content = _report_preview_html(preview)

            self.assertEqual(preview["grid_id"], "grid_001")
            self.assertEqual(preview["rank"], 1)
            self.assertEqual(len(preview["metrics"]), 6)
            self.assertIn("一般观察型", content)
            self.assertIn("未触发过度竞争预警", content)
            self.assertIn("交通可达性", preview["metrics"]["指标"].tolist())

    def test_page_registrations_define_seven_workbench_pages_in_order(self):
        self.assertEqual(
            [page.title for page in PAGE_REGISTRATIONS],
            [
                "项目总览",
                "数据底座",
                "区域对比",
                "网格推荐",
                "地图洞察",
                "智能报告",
                "项目说明",
            ],
        )
        self.assertEqual(
            [page.url_path for page in PAGE_REGISTRATIONS],
            [
                "overview",
                "data-foundation",
                "district-compare",
                "grid-recommendation",
                "map-insight",
                "report-center",
                "project-notes",
            ],
        )
        self.assertTrue(PAGE_REGISTRATIONS[0].default)
        self.assertEqual(
            sum(page.default for page in PAGE_REGISTRATIONS),
            1,
        )

    def test_run_navigation_uses_streamlit_page_and_navigation(self):
        st = FakeNavigationStreamlit()

        run_navigation(st)

        self.assertEqual(len(st.created_pages), 7)
        self.assertEqual(st.created_pages[0].title, "项目总览")
        self.assertTrue(st.created_pages[0].default)
        self.assertEqual(st.navigation_calls[0]["position"], "sidebar")
        self.assertTrue(st.navigation_calls[0]["expanded"])
        self.assertEqual(st.controller.run_count, 1)
        self.assertEqual(st.sidebar.radio_calls, [])

    def test_run_navigation_falls_back_to_sidebar_radio(self):
        calls = []
        registrations = [
            SimpleNamespace(
                title="页面甲",
                url_path="page-a",
                renderer=lambda: calls.append("页面甲"),
                default=True,
            ),
            SimpleNamespace(
                title="页面乙",
                url_path="page-b",
                renderer=lambda: calls.append("页面乙"),
                default=False,
            ),
        ]
        st = FakeNavigationStreamlit(
            selected_fallback="页面乙",
            supports_navigation=False,
        )

        run_navigation(st, registrations=registrations)

        self.assertEqual(
            st.sidebar.radio_calls,
            [("页面", ["页面甲", "页面乙"])],
        )
        self.assertEqual(calls, ["页面乙"])

    def test_run_workbench_applies_theme_and_brand_before_navigation(self):
        st = FakeNavigationStreamlit()

        run_workbench(st)

        self.assertEqual(
            st.page_config_calls,
            [{"page_title": "黔址优选", "layout": "wide"}],
        )
        self.assertEqual(len(st.html_calls), 2)
        self.assertIn("<style>", st.html_calls[0])
        self.assertIn("黔址优选 | 社区商业智能选址决策系统", st.html_calls[1])
        self.assertEqual(st.controller.run_count, 1)

    def test_render_map_page_uses_dynamic_profile_selector_and_st_folium(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            specs = {
                "默认｜社区便利店": make_map_spec(
                    "convenience",
                    "社区便利店",
                    base / "default.csv",
                    base / "default.html",
                ),
                "自定义｜自定义社区业态 (custom_01)": make_map_spec(
                    "custom_01",
                    "自定义社区业态",
                    base / "custom.csv",
                    None,
                ),
            }
            selected = "自定义｜自定义社区业态 (custom_01)"
            st = FakeStreamlit(selected)
            components = FakeComponents()
            rendered = []
            map_object = object()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                map_builder=lambda spec: map_object,
                credential_loader=lambda: None,
                st_folium_func=lambda fig, **kwargs: rendered.append((fig, kwargs)),
            )

            self.assertEqual(st.selectbox_label, "评分方案")
            self.assertEqual(st.selectbox_options, list(specs))
            self.assertEqual(rendered[0][0], map_object)
            self.assertEqual(rendered[0][1]["height"], 680)
            self.assertTrue(rendered[0][1]["use_container_width"])
            self.assertEqual(rendered[0][1]["key"], "site_map_custom_01")
            self.assertEqual(components.calls, [])

    def test_render_map_page_prefers_amap_html_when_credentials_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            label = "默认｜社区便利店"
            spec = make_map_spec(
                "convenience",
                "社区便利店",
                base / "default.csv",
                base / "default.html",
            )
            st = FakeStreamlit(label)
            components = FakeComponents()
            folium_calls = []
            html_calls = []

            render_map_page(
                st,
                components,
                profile_specs={label: spec},
                amap_html_builder=lambda selected, **kwargs: (
                    html_calls.append((selected, kwargs)) or "<div>amap</div>"
                ),
                credential_loader=lambda: object(),
                st_folium_func=lambda fig, **kwargs: folium_calls.append(
                    (fig, kwargs)
                ),
            )

            self.assertEqual(len(components.calls), 1)
            self.assertIn("amap", components.calls[0]["content"])
            self.assertEqual(html_calls[0][0], spec)
            self.assertEqual(folium_calls, [])

    def test_render_map_page_uses_folium_when_compatibility_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            label = "默认｜社区便利店"
            spec = make_map_spec(
                "convenience",
                "社区便利店",
                base / "default.csv",
                base / "default.html",
            )
            st = FakeStreamlit(label, toggle_value=True)
            components = FakeComponents()
            map_object = object()
            folium_calls = []

            render_map_page(
                st,
                components,
                profile_specs={label: spec},
                map_builder=lambda selected: map_object,
                amap_html_builder=lambda selected, **kwargs: "<div>amap</div>",
                credential_loader=lambda: object(),
                st_folium_func=lambda fig, **kwargs: folium_calls.append(
                    (fig, kwargs)
                ),
            )

            self.assertEqual(folium_calls[0][0], map_object)
            self.assertEqual(components.calls, [])

    def test_render_map_page_uses_workbench_control_and_map_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            label = "默认｜社区便利店"
            specs = {
                label: make_map_spec(
                    "convenience",
                    "社区便利店",
                    base / "default.csv",
                    base / "default.html",
                )
            }
            st = FakeStreamlit(label)
            rendered = []

            render_map_page(
                st,
                FakeComponents(),
                profile_specs=specs,
                map_builder=lambda spec: object(),
                credential_loader=lambda: None,
                st_folium_func=lambda fig, **kwargs: rendered.append((fig, kwargs)),
                use_workbench_layout=True,
                show_header=False,
            )

            self.assertEqual(st.column_calls, [([1, 4], "large")])
            self.assertIn("地图参数", st.subheaders)
            self.assertEqual(len(rendered), 1)

    def test_render_map_page_falls_back_to_default_static_html(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            html_path = base / "default.html"
            html_path.write_text("<p>default map</p>", encoding="utf-8")
            label = "默认｜社区便利店"
            specs = {
                label: make_map_spec(
                    "convenience",
                    "社区便利店",
                    base / "default.csv",
                    html_path,
                )
            }
            st = FakeStreamlit(label)
            components = FakeComponents()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                credential_loader=lambda: None,
                st_folium_func=None,
            )

            self.assertEqual(len(components.calls), 1)
            self.assertIn("default map", components.calls[0]["content"])
            self.assertEqual(components.calls[0]["height"], 680)

    def test_render_map_page_does_not_fallback_custom_profile_to_default_html(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            label = "自定义｜自定义社区业态 (custom_01)"
            specs = {
                label: make_map_spec(
                    "custom_01",
                    "自定义社区业态",
                    base / "custom.csv",
                    None,
                )
            }
            st = FakeStreamlit(label)
            components = FakeComponents()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                credential_loader=lambda: None,
                st_folium_func=None,
            )

            self.assertEqual(components.calls, [])
            self.assertTrue(
                any("streamlit-folium" in message for message in st.errors)
            )

    def test_render_report_page_calls_deepseek_only_on_button_and_caches_result(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = write_report_result(base / "result.csv")
            spec = make_report_spec(result_path)
            specs = {"默认｜社区便利店": spec}
            session_state = {}
            generator = Mock(
                return_value=ReportGenerationResult(
                    content="# 智能报告",
                    mode="deepseek",
                    model="deepseek-v4-pro",
                    used_fallback=False,
                )
            )

            idle = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
                session_state=session_state,
            )
            render_report_page(
                idle,
                "社区便利店",
                profile_specs=specs,
                report_generator_func=generator,
            )
            generator.assert_not_called()
            self.assertEqual(len(idle.selectboxes["评价网格"]), 41)

            clicked = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
                clicked_buttons={"生成智能报告"},
                session_state=session_state,
            )
            render_report_page(
                clicked,
                "社区便利店",
                profile_specs=specs,
                report_generator_func=generator,
            )
            generator.assert_called_once()
            self.assertIn("deepseek-v4-pro", clicked.infos[0])
            self.assertEqual(clicked.markdowns, ["# 智能报告"])
            self.assertIn(
                {"border": False, "key": "report-content"},
                clicked.container_calls,
            )
            self.assertEqual(
                clicked.status_calls[0]["label"],
                "正在生成智能报告，通常需要数秒，请勿重复点击。",
            )
            self.assertEqual(clicked.status_calls[0]["state"], "running")
            self.assertEqual(
                clicked.status_updates,
                [
                    {
                        "label": "智能报告生成完成。",
                        "state": "complete",
                        "expanded": False,
                    }
                ],
            )

            refreshed = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
                session_state=session_state,
            )
            render_report_page(
                refreshed,
                "社区便利店",
                profile_specs=specs,
                report_generator_func=generator,
            )
            generator.assert_called_once()
            self.assertEqual(refreshed.markdowns, ["# 智能报告"])
            self.assertEqual(refreshed.status_calls, [])

    def test_render_report_page_uses_workbench_columns_and_idle_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            spec = make_report_spec(write_report_result(base / "result.csv"))
            generator = Mock()
            st = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
            )

            render_report_page(
                st,
                profile_specs={"默认｜社区便利店": spec},
                report_generator_func=generator,
                use_workbench_layout=True,
                show_header=False,
            )

            generator.assert_not_called()
            self.assertEqual(st.column_calls, [([1, 2.4], "large")])
            self.assertTrue(
                any("生成智能报告" in message for message in st.infos)
            )

    def test_render_report_page_offers_template_after_deepseek_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            spec = make_report_spec(write_report_result(base / "result.csv"))
            specs = {"默认｜社区便利店": spec}
            session_state = {}
            generator = Mock(side_effect=Exception("DeepSeek unavailable"))

            failed = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
                clicked_buttons={"生成智能报告"},
                session_state=session_state,
            )
            render_report_page(
                failed,
                "社区便利店",
                profile_specs=specs,
                report_generator_func=generator,
            )
            self.assertIn("DeepSeek unavailable", failed.errors[0])
            self.assertEqual(
                failed.status_updates,
                [
                    {
                        "label": "智能报告生成失败。",
                        "state": "error",
                        "expanded": True,
                    }
                ],
            )

            generator.side_effect = None
            generator.return_value = ReportGenerationResult(
                content="# 模板报告",
                mode="template",
                model=None,
                used_fallback=False,
            )
            fallback = FakeStreamlit(
                selected_label={"评分方案": "默认｜社区便利店"},
                clicked_buttons={"使用模板报告"},
                session_state=session_state,
            )
            render_report_page(
                fallback,
                "社区便利店",
                profile_specs=specs,
                report_generator_func=generator,
            )
            self.assertEqual(generator.call_args.kwargs["use_llm"], False)
            self.assertEqual(fallback.markdowns, ["# 模板报告"])

    def test_render_grid_recommendation_page_uses_full_district_ranking_and_fixed_table_height(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = base / "result.csv"
            scoring_path = base / "scoring.csv"
            rows = []
            for index in range(1, 7):
                rows.append(
                    {
                        "grid_id": f"g{index}",
                        "district_name": "甲区",
                        "centroid_lon": 106.7,
                        "centroid_lat": 26.6,
                        "area_km2": 1.0,
                        "data_source": "amap_boundary",
                        "poi_total_count": 10,
                        "has_poi_activity": True,
                        "traffic_accessibility": 50.0,
                        "consumption_potential": 50.0,
                        "employment_customer_proxy": 50.0,
                        "business_atmosphere": 50.0,
                        "convenience_synergy_score": 50.0,
                        "light_food_synergy_score": 50.0,
                        "convenience_competition_pressure": 50.0,
                        "convenience_competition_score": 50.0,
                        "light_food_competition_pressure": 50.0,
                        "convenience_score": 100.0 - index,
                        "convenience_rank": index,
                        "convenience_district_rank": index,
                        "convenience_main_advantage": "交通可达性",
                        "convenience_main_risk": "竞争压力较高",
                        "convenience_recommendation_level": "推荐",
                        "convenience_demand_customer_proxy": 50.0,
                        "convenience_market_stage": "一般观察型",
                        "convenience_competition_alert": "未触发过度竞争预警",
                        "convenience_diagnosis_summary": "一般观察型；未触发过度竞争预警。",
                    }
                )
            pd.DataFrame(rows).to_csv(result_path, index=False, encoding="utf-8-sig")
            pd.DataFrame(
                [
                    {
                        "grid_id": "g1",
                        "district_name": "甲区",
                        "poi_total_count": 10,
                        "has_poi_activity": True,
                        "traffic_accessibility": 50.0,
                        "consumption_potential": 50.0,
                        "employment_customer_proxy": 50.0,
                        "business_atmosphere": 50.0,
                        "convenience_synergy_score": 50.0,
                        "light_food_synergy_score": 50.0,
                        "convenience_competition_pressure": 50.0,
                        "light_food_competition_pressure": 50.0,
                    }
                ]
            ).to_csv(scoring_path, index=False, encoding="utf-8-sig")
            spec = MapProfileSpec(
                profile_id="convenience",
                profile_name="社区便利店",
                template_id="community_retail",
                weights={
                    "traffic_accessibility": 0.20,
                    "consumption_potential": 0.25,
                    "employment_customer_proxy": 0.10,
                    "synergy_score": 0.20,
                    "competition_pressure": 0.15,
                    "business_atmosphere": 0.10,
                },
                result_path=result_path,
                metadata_path=base / "profile_metadata.json",
                static_html_path=None,
                score_field="convenience_score",
                rank_field="convenience_rank",
                district_rank_field="convenience_district_rank",
                competition_score_field="convenience_competition_score",
                competition_pressure_field="convenience_competition_pressure",
                advantage_field="convenience_main_advantage",
                risk_field="convenience_main_risk",
                level_field="convenience_recommendation_level",
                synergy_field="convenience_synergy_score",
                demand_proxy_field="convenience_demand_customer_proxy",
                market_stage_field="convenience_market_stage",
                competition_alert_field="convenience_competition_alert",
                diagnosis_summary_field="convenience_diagnosis_summary",
            )
            st = FakeStreamlit(
                selected_label={
                    "方案来源": "默认｜社区便利店",
                    "推荐范围": "甲区",
                    "市场阶段": "全部",
                    "竞争状态": "全部",
                    "查看网格六维分解": "g6",
                }
            )

            with unittest.mock.patch(
                "src.web.pages.grid_recommendation.load_scoring_input",
                return_value=pd.read_csv(scoring_path),
            ), unittest.mock.patch(
                "src.web.pages.grid_recommendation.load_profile_options",
                return_value={"默认｜社区便利店": spec},
            ):
                render_grid_recommendation_page(st)

            self.assertIn("甲区全部排名（6 个网格）", st.subheaders)
            self.assertEqual(
                st.dataframe_calls[0][0]["网格标识"].tolist(),
                [f"g{index}" for index in range(1, 7)],
            )
            self.assertEqual(st.dataframe_calls[0][1]["height"], 360)
            self.assertEqual(
                st.selectboxes["查看网格六维分解"],
                [f"g{index}" for index in range(1, 7)],
            )

    def test_app_script_imports_when_streamlit_runs_file_path(self):
        project_root = Path(__file__).resolve().parents[2]
        src_dir = project_root / "src"
        original_path = list(sys.path)
        removed_modules = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name == "src"
            or name.startswith("src.")
            or name == "config"
            or name.startswith("reporting")
        }

        try:
            filtered_path = [
                entry
                for entry in original_path
                if Path(entry or ".").resolve() != project_root
            ]
            sys.path[:] = [str(src_dir), *filtered_path]

            namespace = runpy.run_path(str(src_dir / "app.py"), run_name="streamlit_app")

            self.assertTrue(callable(namespace["main"]))
        finally:
            sys.path[:] = original_path
            sys.modules.update(removed_modules)


if __name__ == "__main__":
    unittest.main()
