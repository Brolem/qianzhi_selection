import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.reporting.report_generator import (
    MissingQianwenConfigError,
    export_report,
    generate_site_report,
    generate_template_report,
)


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Completion:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Completion("# 千问生成报告\n\n## 一、候选网格基本信息\n\n来自大模型。")


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class _Client:
    def __init__(self):
        self.chat = _Chat()


def _write_grid_result(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "region_id": "grid_8316193_000003",
                "grid_id": "grid_8316193_000003",
                "grid_region_name": "万里路街道",
                "centroid_lon": 106.9220863849578,
                "centroid_lat": 27.678994040462996,
                "area_km2": 0.38686955376578064,
                "traffic_accessibility": 0.7510490788980837,
                "consumption_potential": 0.6663160214978482,
                "synergy_score": 0.5071060752424686,
                "competition_pressure": 0.29131602149784813,
                "development_basis": 0.5750000000000001,
                "convenience_score": 0.6549992858479071,
                "light_catering_score": 0.6470387885351381,
                "main_advantage": "交通可达性",
                "main_risk": "共生业态",
            }
        ]
    ).to_csv(path, index=False, encoding="utf-8-sig")


class ReportGeneratorTests(unittest.TestCase):
    def test_generate_site_report_calls_qianwen_chat_completion_with_real_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = Path(tmp_dir) / "grid_stage_score_result.csv"
            _write_grid_result(result_path)
            client = _Client()

            report = generate_site_report(
                "grid_8316193_000003",
                "社区便利店",
                result_path=result_path,
                use_llm=True,
                llm_client=client,
            )

            self.assertIn("千问生成报告", report)
            self.assertEqual(len(client.chat.completions.calls), 1)
            call = client.chat.completions.calls[0]
            self.assertEqual(call["model"], "qwen3.7-plus")
            prompt = call["messages"][1]["content"]
            for text in ["grid_8316193_000003", "社区便利店", "0.6549992858479071", "交通可达性", "共生业态"]:
                self.assertIn(text, prompt)

    def test_generate_site_report_requires_dashscope_api_key_for_llm_without_client(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = Path(tmp_dir) / "grid_stage_score_result.csv"
            _write_grid_result(result_path)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(MissingQianwenConfigError):
                    generate_site_report(
                        "grid_8316193_000003",
                        "社区便利店",
                        result_path=result_path,
                        use_llm=True,
                    )

    def test_template_report_has_ten_sections_and_missing_data_notice(self):
        record = pd.read_csv(_make_grid_result_file()).iloc[0].to_dict()

        report = generate_template_report(record, "轻餐饮")

        for heading in [
            "## 一、候选网格基本信息",
            "## 二、适配业态判断",
            "## 三、交通可达性分析",
            "## 四、消费潜力分析",
            "## 五、共生业态分析",
            "## 六、竞争压力分析",
            "## 七、主要优势",
            "## 八、主要风险",
            "## 九、经营建议",
            "## 十、数据来源与限制说明",
        ]:
            self.assertIn(heading, report)
        self.assertIn("模板生成", report)
        self.assertIn("当前未接入，后续可补充", report)

    def test_export_report_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result_path = Path(tmp_dir) / "grid_stage_score_result.csv"
            output_path = Path(tmp_dir) / "report.md"
            _write_grid_result(result_path)

            path = export_report(
                "grid_8316193_000003",
                "轻餐饮",
                output_path=output_path,
                result_path=result_path,
                use_llm=False,
            )

            self.assertEqual(path, output_path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("grid_8316193_000003", text)
            self.assertIn("轻餐饮", text)


def _make_grid_result_file() -> Path:
    tmp_dir = tempfile.TemporaryDirectory()
    path = Path(tmp_dir.name) / "grid_stage_score_result.csv"
    _write_grid_result(path)
    _make_grid_result_file._tmp_dir = tmp_dir
    return path


if __name__ == "__main__":
    unittest.main()
