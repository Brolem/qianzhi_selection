import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.core.profile_catalog import ResultProfileSpec
from src.presentation import report_generator


WEIGHTS = {
    "traffic_accessibility": 0.20,
    "consumption_potential": 0.25,
    "employment_customer_proxy": 0.10,
    "synergy_score": 0.20,
    "competition_pressure": 0.15,
    "business_atmosphere": 0.10,
}


def make_profile(result_path: Path, profile_id: str = "convenience") -> ResultProfileSpec:
    custom = profile_id.startswith("custom_")
    return ResultProfileSpec(
        profile_id=profile_id,
        profile_name="自定义社区业态" if custom else "社区便利店",
        template_id="community_retail",
        weights=WEIGHTS,
        result_path=result_path,
        metadata_path=result_path.parent / "profile_metadata.json",
        static_html_path=None,
        score_field="profile_score" if custom else "convenience_score",
        rank_field="profile_rank" if custom else "convenience_rank",
        district_rank_field="district_profile_rank" if custom else "convenience_district_rank",
        competition_score_field="profile_competition_score" if custom else "convenience_competition_score",
        competition_pressure_field="convenience_competition_pressure",
        advantage_field="profile_main_advantage" if custom else "convenience_main_advantage",
        risk_field="profile_main_risk" if custom else "convenience_main_risk",
        level_field="profile_recommendation_level" if custom else "convenience_recommendation_level",
        synergy_field="convenience_synergy_score",
        demand_proxy_field="profile_demand_customer_proxy" if custom else "convenience_demand_customer_proxy",
        market_stage_field="profile_market_stage" if custom else "convenience_market_stage",
        competition_alert_field="profile_competition_alert" if custom else "convenience_competition_alert",
        diagnosis_summary_field="profile_diagnosis_summary" if custom else "convenience_diagnosis_summary",
    )


def write_result(path: Path, active: bool = True, custom: bool = False) -> Path:
    row = {
        "grid_id": "grid_520103_000078",
        "district_name": "云岩区",
        "adcode": "520103",
        "centroid_lon": 106.7,
        "centroid_lat": 26.6,
        "area_km2": 0.98,
        "data_source": "amap_boundary",
        "poi_total_count": 42 if active else 0,
        "poi_category_coverage": 10 if active else 0,
        "has_poi_activity": active,
        "traffic_accessibility": 82.0 if active else 0.0,
        "consumption_potential": 88.0 if active else 0.0,
        "employment_customer_proxy": 75.0 if active else 0.0,
        "business_atmosphere": 79.0 if active else 0.0,
        "convenience_synergy_score": 84.0 if active else 0.0,
        "convenience_competition_pressure": 31.0 if active else 0.0,
    }
    if custom:
        row.update(
            {
                "profile_id": "custom_01",
                "profile_name": "自定义社区业态",
                "template_id": "community_retail",
                "profile_competition_score": 69.0,
                "profile_score": 83.0 if active else 0.0,
                "profile_rank": 1 if active else None,
                "district_profile_rank": 1 if active else None,
                "profile_main_advantage": "消费潜力",
                "profile_main_risk": "竞争压力较高",
                "profile_recommendation_level": "推荐" if active else "暂不推荐",
                "profile_demand_customer_proxy": 81.5 if active else 0.0,
                "profile_market_stage": "成熟商圈型" if active else "无 POI 活动",
                "profile_competition_alert": "过度竞争预警" if active else "不参与诊断",
                "profile_diagnosis_summary": (
                    "成熟商圈型；触发过度竞争预警。"
                    if active
                    else "无 POI 活动，不参与区域市场诊断。"
                ),
            }
        )
    else:
        row.update(
            {
                "convenience_competition_score": 69.0,
                "convenience_score": 83.0 if active else 0.0,
                "convenience_rank": 1 if active else None,
                "convenience_district_rank": 1 if active else None,
                "convenience_main_advantage": "消费潜力",
                "convenience_main_risk": "竞争压力较高",
                "convenience_recommendation_level": "推荐" if active else "暂不推荐",
                "convenience_demand_customer_proxy": 81.5 if active else 0.0,
                "convenience_market_stage": "成熟商圈型" if active else "无 POI 活动",
                "convenience_competition_alert": "过度竞争预警" if active else "不参与诊断",
                "convenience_diagnosis_summary": (
                    "成熟商圈型；触发过度竞争预警。"
                    if active
                    else "无 POI 活动，不参与区域市场诊断。"
                ),
            }
        )
    pd.DataFrame([row]).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def valid_analysis_payload() -> dict:
    return {
        "schema_version": "1.0",
        "sections": {
            "basic_information": {
                "analysis": "该网格具备完整的基础评价信息，可进入后续研判。",
                "evidence_fields": [
                    "grid.district_name",
                    "grid.poi_total_count",
                ],
            },
            "business_fit": {
                "analysis": "当前方案下的推荐等级与相对排名表现较好。",
                "evidence_fields": [
                    "profile.profile_name",
                    "recommendation.level",
                    "recommendation.global_rank",
                    "diagnosis.market_stage",
                ],
            },
            "traffic_accessibility": {
                "analysis": "交通配套类兴趣点形成了较强的相对支撑。",
                "evidence_fields": ["metrics.traffic_accessibility"],
            },
            "consumption_potential": {
                "analysis": "生活服务设施对日常消费需求形成较强支撑。",
                "evidence_fields": ["metrics.consumption_potential"],
            },
            "employment_customer_proxy": {
                "analysis": "办公与活动场景类兴趣点可提供客群代理支撑。",
                "evidence_fields": ["metrics.employment_customer_proxy"],
            },
            "synergy": {
                "analysis": "相关配套业态具有较好的相对协同条件。",
                "evidence_fields": ["metrics.synergy_score"],
            },
            "competition": {
                "analysis": "同类设施集聚带来竞争风险，需要结合现场经营状态核验。",
                "evidence_fields": [
                    "metrics.competition_pressure",
                    "metrics.competition_score",
                    "diagnosis.demand_customer_proxy",
                    "diagnosis.competition_alert",
                ],
            },
            "business_atmosphere": {
                "analysis": "商业设施集聚度与当前方案权重共同支撑综合评价。",
                "evidence_fields": [
                    "metrics.business_atmosphere",
                    "profile.weights",
                ],
            },
            "strengths_and_risks": {
                "analysis": "主要优势较突出，同时应重点核验已识别风险。",
                "evidence_fields": [
                    "recommendation.main_advantage",
                    "recommendation.main_risk",
                    "diagnosis.diagnosis_summary",
                ],
            },
            "operating_suggestions": {
                "items": [
                    {
                        "suggestion": "优先核验主要优势对应设施的实际可达性与稳定性。",
                        "basis_fields": ["recommendation.main_advantage"],
                    },
                    {
                        "suggestion": "通过现场踏勘确认同类门店经营状态及租金条件。",
                        "basis_fields": ["recommendation.main_risk"],
                    },
                ],
            },
            "limitations": {
                "analysis": "结论仅用于统一样本口径下的相对比较，仍需现场调研。",
                "evidence_fields": [
                    "official_data.scope",
                    "method_boundaries",
                ],
            },
        },
        "quality_check": {
            "all_claims_grounded": True,
            "competition_direction_checked": True,
            "no_unsupported_predictions": True,
            "all_sections_complete": True,
        },
    }


def valid_analysis_json() -> str:
    return json.dumps(valid_analysis_payload(), ensure_ascii=False)


class FakeCompletion:
    def __init__(self, content):
        message = type("FakeMessage", (), {"content": content})()
        self.choices = [type("FakeChoice", (), {"message": message})()]


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeCompletion(outcome)


class FakeClient:
    def __init__(self, outcomes):
        completions = FakeCompletions(outcomes)
        self.chat = type("FakeChat", (), {"completions": completions})()


class FakeApiError(RuntimeError):
    def __init__(self, status_code, message="api error"):
        super().__init__(message)
        self.status_code = status_code


class ReportGeneratorTests(unittest.TestCase):
    def test_deepseek_pro_uses_non_thinking_mode_and_v2_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            client = FakeClient([valid_analysis_json()])

            result = report_generator.generate_site_report(
                "grid_520103_000078",
                make_profile(result_path),
                llm_client=client,
            )

            self.assertEqual(result.mode, "deepseek")
            self.assertEqual(result.model, "deepseek-v4-pro")
            self.assertFalse(result.used_fallback)
            call = client.chat.completions.calls[0]
            self.assertEqual(call["model"], "deepseek-v4-pro")
            self.assertEqual(call["extra_body"], {"thinking": {"type": "disabled"}})
            self.assertEqual(
                call["response_format"],
                {"type": "json_object"},
            )
            system_prompt = call["messages"][0]["content"]
            for text in [
                "<metric_dictionary>",
                "公交站、地铁站、停车场",
                "低竞争得分 = 100 - 竞争压力",
                "<evidence_rules>",
                "<allowed_evidence_fields>",
                '"business_fit"',
                '"profile.weights"',
                "<output_schema>",
                "JSON",
            ]:
                self.assertIn(text, system_prompt)
            prompt = call["messages"][1]["content"]
            for text in [
                "grid_520103_000078",
                "云岩区",
                "83.0",
                "employment_customer_proxy",
                "贵州省级",
                "不参与网格评分",
                "demand_customer_proxy",
                "成熟商圈型",
                "过度竞争预警",
            ]:
                self.assertIn(text, prompt)
            self.assertIn("# 云岩区 社区便利店选址报告", result.content)
            self.assertIn("综合得分：83.00", result.content)
            self.assertIn("竞争压力：31.00", result.content)
            self.assertIn("低竞争得分：69.00", result.content)
            self.assertIn("市场阶段：成熟商圈型", result.content)
            self.assertIn("竞争状态：过度竞争预警", result.content)
            self.assertIn(
                "交通配套类兴趣点形成了较强的相对支撑。",
                result.content,
            )

    def test_analysis_json_requires_valid_evidence_and_quality_checks(self):
        payload = valid_analysis_payload()
        payload["sections"]["traffic_accessibility"]["evidence_fields"] = [
            "metrics.road_density"
        ]
        with self.assertRaisesRegex(
            report_generator.InvalidReportContentError,
            "traffic_accessibility.*metrics.road_density",
        ):
            report_generator.validate_report_analysis(
                json.dumps(payload, ensure_ascii=False)
            )

        payload = valid_analysis_payload()
        payload["quality_check"]["competition_direction_checked"] = False
        with self.assertRaisesRegex(
            report_generator.InvalidReportContentError,
            "competition_direction_checked",
        ):
            report_generator.validate_report_analysis(
                json.dumps(payload, ensure_ascii=False)
            )

    def test_analysis_json_rejects_model_written_numbers_and_unsupported_claims(self):
        for analysis in [
            "交通可达性达到八十二分。",
            "该网格路网密度较高。",
            "建议优先选择社区出入口的具体铺位。",
        ]:
            with self.subTest(analysis=analysis):
                payload = valid_analysis_payload()
                payload["sections"]["traffic_accessibility"][
                    "analysis"
                ] = analysis
                with self.assertRaises(
                    report_generator.InvalidReportContentError
                ):
                    report_generator.validate_report_analysis(
                        json.dumps(payload, ensure_ascii=False)
                    )

    def test_generate_site_report_repairs_model_written_numbers_in_analysis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            payload = valid_analysis_payload()
            payload["sections"]["basic_information"]["analysis"] = (
                "该网格位于云岩区，面积约1平方公里，POI总数为125个，覆盖12个类别，表明区域内业态相对丰富。"
            )
            payload["sections"]["business_fit"]["analysis"] = (
                "该网格被诊断为成熟商圈型，且综合评分在云岩区排名第5，全市排名第6，属于推荐级别，适合社区便利店业态。"
            )
            client = FakeClient([json.dumps(payload, ensure_ascii=False)])

            result = report_generator.generate_site_report(
                "grid_520103_000078",
                make_profile(result_path),
                llm_client=client,
            )

            self.assertEqual(result.mode, "deepseek")
            self.assertFalse(result.used_fallback)
            self.assertIn(
                "该网格位于云岩区，基础信息完整，可作为当前方案下的有效研判对象。",
                result.content,
            )
            self.assertIn(
                "当前方案下该网格处于前列，推荐等级与成熟商圈型诊断相互一致，适合社区便利店业态。",
                result.content,
            )
            self.assertNotIn("POI总数为125个", result.content)
            self.assertNotIn("覆盖12个类别", result.content)

    def test_limitations_section_may_state_explicit_method_boundaries(self):
        payload = valid_analysis_payload()
        payload["sections"]["limitations"]["analysis"] = (
            "结论不提供门牌号或具体铺位推荐，相关条件需现场核验。"
        )

        result = report_generator.validate_report_analysis(
            json.dumps(payload, ensure_ascii=False)
        )

        self.assertIn(
            "具体铺位",
            result["sections"]["limitations"]["analysis"],
        )

    def test_empty_content_retries_same_model_once_without_flash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            client = FakeClient(["", valid_analysis_json()])

            result = report_generator.generate_site_report(
                "grid_520103_000078",
                make_profile(result_path),
                llm_client=client,
            )

            self.assertFalse(result.used_fallback)
            self.assertEqual(
                [call["model"] for call in client.chat.completions.calls],
                ["deepseek-v4-pro", "deepseek-v4-pro"],
            )

    def test_retryable_primary_errors_use_flash_once(self):
        import httpx
        from openai import APIConnectionError, APITimeoutError

        request = httpx.Request("POST", "https://api.deepseek.com")
        errors = [
            FakeApiError(404),
            FakeApiError(429),
            FakeApiError(500),
            FakeApiError(503),
            APIConnectionError(request=request),
            APITimeoutError(request),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__, status=getattr(error, "status_code", None)):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result_path = write_result(Path(tmp_dir) / "result.csv")
                    client = FakeClient([error, valid_analysis_json()])

                    result = report_generator.generate_site_report(
                        "grid_520103_000078",
                        make_profile(result_path),
                        llm_client=client,
                    )

                    self.assertTrue(result.used_fallback)
                    self.assertEqual(result.model, "deepseek-v4-flash")
                    self.assertEqual(
                        [call["model"] for call in client.chat.completions.calls],
                        ["deepseek-v4-pro", "deepseek-v4-flash"],
                    )

    def test_non_retryable_errors_do_not_use_flash(self):
        for status_code in [400, 401, 402, 403, 422]:
            with self.subTest(status_code=status_code):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result_path = write_result(Path(tmp_dir) / "result.csv")
                    client = FakeClient([FakeApiError(status_code)])
                    with self.assertRaises(FakeApiError):
                        report_generator.generate_site_report(
                            "grid_520103_000078",
                            make_profile(result_path),
                            llm_client=client,
                        )
                    self.assertEqual(len(client.chat.completions.calls), 1)

    def test_invalid_model_content_stops_without_flash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            for content in [
                "不是 JSON",
                json.dumps({"schema_version": "1.0"}, ensure_ascii=False),
            ]:
                with self.subTest(content=content):
                    client = FakeClient([content])
                    with self.assertRaises(report_generator.InvalidReportContentError):
                        report_generator.generate_site_report(
                            "grid_520103_000078",
                            make_profile(result_path),
                            llm_client=client,
                        )
                    self.assertEqual(len(client.chat.completions.calls), 1)

    def test_template_report_has_eleven_sections_and_data_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            result = report_generator.generate_site_report(
                "grid_520103_000078",
                make_profile(result_path),
                use_llm=False,
            )

            self.assertEqual(result.mode, "template")
            self.assertIsNone(result.model)
            for heading in report_generator.REPORT_HEADINGS:
                self.assertIn(heading, result.content)
            for text in [
                "贵州省级",
                "不参与网格评分",
                "关键词 POI 样本",
                "不是门牌号级推荐",
                "就业/办公客群代理",
                "需求客群代理",
                "不是真实客流",
                "市场阶段",
                "竞争状态",
            ]:
                self.assertIn(text, result.content)

    def test_report_payload_uses_program_generated_market_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv")
            profile = make_profile(result_path)
            record = report_generator.load_profile_results(profile).iloc[0].to_dict()

            payload = report_generator.build_report_payload(
                record,
                profile,
                {
                    "scope": "贵州省级",
                    "usage": "不参与网格评分",
                },
            )

            self.assertEqual(payload["diagnosis"]["demand_customer_proxy"], 81.5)
            self.assertEqual(payload["diagnosis"]["market_stage"], "成熟商圈型")
            self.assertEqual(
                payload["diagnosis"]["competition_alert"],
                "过度竞争预警",
            )
            self.assertIn(
                "不得修改程序生成的诊断标签",
                report_generator.build_report_system_prompt(),
            )

    def test_inactive_grid_and_missing_key_stop_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = write_result(Path(tmp_dir) / "result.csv", active=False)
            with self.assertRaisesRegex(ValueError, "无 POI 活动"):
                report_generator.generate_site_report(
                    "grid_520103_000078",
                    make_profile(result_path),
                    use_llm=False,
                )

            active_path = write_result(Path(tmp_dir) / "active.csv")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(report_generator.MissingDeepSeekConfigError):
                    report_generator.generate_site_report(
                        "grid_520103_000078",
                        make_profile(active_path),
                    )

    def test_custom_profile_and_atomic_export_use_profile_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            result_path = write_result(base / "custom.csv", custom=True)
            profile = make_profile(result_path, "custom_01")
            report = report_generator.generate_site_report(
                "grid_520103_000078",
                profile,
                use_llm=False,
            )

            output = report_generator.export_report(
                report,
                "grid_520103_000078",
                profile,
                reports_dir=base / "reports",
            )

            self.assertEqual(output.parent.name, "custom_01")
            self.assertEqual(output.name, "grid_520103_000078_选址报告.md")
            self.assertEqual(output.read_text(encoding="utf-8"), report.content)

    def test_client_uses_configured_timeout_and_one_sdk_retry(self):
        fake_openai = object()
        config = {
            "llm": {
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "timeout_seconds": 60,
                "primary_max_retries": 1,
            }
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=fake_openai) as constructor:
                client = report_generator.create_deepseek_client(config=config)

        self.assertIs(client, fake_openai)
        constructor.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            timeout=60.0,
            max_retries=1,
        )


if __name__ == "__main__":
    unittest.main()
