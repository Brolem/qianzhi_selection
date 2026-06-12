import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.profile_catalog import ResultProfileSpec
from src.reporting import report_generator


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
            }
        )
    pd.DataFrame([row]).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def valid_report() -> str:
    headings = [
        "## 一、评价网格基本信息",
        "## 二、适配业态与推荐等级",
        "## 三、交通可达性分析",
        "## 四、消费潜力分析",
        "## 五、就业/办公客群代理分析",
        "## 六、共生业态分析",
        "## 七、竞争压力分析",
        "## 八、商业氛围与权重方案",
        "## 九、主要优势与风险",
        "## 十、经营建议",
        "## 十一、数据来源与限制说明",
    ]
    return "# 智能选址报告\n\n" + "\n\n".join(
        f"{heading}\n\n测试内容。" for heading in headings
    )


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
            client = FakeClient([valid_report()])

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
            prompt = call["messages"][1]["content"]
            for text in [
                "grid_520103_000078",
                "云岩区",
                "83.0",
                "employment_customer_proxy",
                "贵州省级",
                "不参与网格评分",
            ]:
                self.assertIn(text, prompt)

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
                    client = FakeClient([error, valid_report()])

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
            for content in ["", "## 一、评价网格基本信息\n\n不完整"]:
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
            ]:
                self.assertIn(text, result.content)

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
