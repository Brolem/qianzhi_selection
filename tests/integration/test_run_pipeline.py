import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


class RunPipelineTests(unittest.TestCase):
    def setUp(self):
        from scripts import run_pipeline

        self.pipeline = run_pipeline

    def test_default_stage_commands_are_offline_and_use_real_modules(self):
        options = self.pipeline.PipelineOptions()

        stages = self.pipeline.build_stage_commands(
            options,
            python_executable="python-test",
        )

        self.assertEqual(
            [stage.name for stage in stages],
            [
                "feature_engineering",
                "scoring",
                "maps",
                "report_convenience",
                "report_light_food",
            ],
        )
        self.assertEqual(
            stages[0].command,
            ("python-test", "-m", "src.modeling.feature_engineering"),
        )
        self.assertEqual(
            stages[3].command,
            (
                "python-test",
                "-m",
                "src.presentation.report_generator",
                "--profile",
                "convenience",
                "--template",
            ),
        )
        self.assertNotIn("src.pipeline.official.official_pipeline", str(stages))
        self.assertNotIn("src.pipeline.poi_fetcher", str(stages))

    def test_optional_flags_add_exact_online_and_llm_stages(self):
        options = self.pipeline.PipelineOptions(
            refresh_official=True,
            refresh_amap=True,
            with_llm=True,
        )

        stages = self.pipeline.build_stage_commands(
            options,
            python_executable="python-test",
        )

        self.assertEqual(
            [stage.name for stage in stages],
            [
                "official_data",
                "districts",
                "grids",
                "poi",
                "feature_engineering",
                "scoring",
                "maps",
                "report_convenience",
                "report_light_food",
            ],
        )
        self.assertEqual(
            stages[3].command,
            ("python-test", "-m", "src.pipeline.poi_fetcher"),
        )
        self.assertNotIn("--template", stages[-1].command)

    def test_preflight_requires_exact_keys_and_official_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            options = self.pipeline.PipelineOptions(
                refresh_official=True,
                refresh_amap=True,
                with_llm=True,
            )

            with self.assertRaisesRegex(
                self.pipeline.PipelinePreflightError,
                "AMAP_KEY",
            ):
                self.pipeline.validate_preflight(
                    options,
                    project_root=root,
                    environ={},
                )

            with self.assertRaisesRegex(
                self.pipeline.PipelinePreflightError,
                "DEEPSEEK_API_KEY",
            ):
                self.pipeline.validate_preflight(
                    options,
                    project_root=root,
                    environ={"AMAP_KEY": "amap-secret"},
                )

            with self.assertRaisesRegex(
                self.pipeline.PipelinePreflightError,
                "宏观经济经济运行-指标数据.xlsx",
            ):
                self.pipeline.validate_preflight(
                    options,
                    project_root=root,
                    environ={
                        "AMAP_KEY": "amap-secret",
                        "DEEPSEEK_API_KEY": "deepseek-secret",
                    },
                )

    def test_default_preflight_requires_tracked_step4_to_step6_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            with self.assertRaisesRegex(
                self.pipeline.PipelinePreflightError,
                "target_districts.csv",
            ):
                self.pipeline.validate_preflight(
                    self.pipeline.PipelineOptions(),
                    project_root=root,
                    environ={},
                )

    def test_stage_failure_stops_following_commands_and_writes_summary(self):
        calls = []

        def runner(command, *, cwd):
            calls.append(tuple(command))
            if len(calls) == 2:
                raise subprocess.CalledProcessError(1, command)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_baseline_inputs(root)

            with self.assertRaisesRegex(
                self.pipeline.PipelineExecutionError,
                "scoring",
            ):
                self.pipeline.run_pipeline(
                    self.pipeline.PipelineOptions(),
                    project_root=root,
                    command_runner=runner,
                    output_validator=lambda **_: {},
                )

            self.assertEqual(len(calls), 2)
            summary = (
                root / "outputs" / "results" / "pipeline_run_summary.md"
            ).read_text(encoding="utf-8")
            self.assertIn("失败阶段：`scoring`", summary)
            self.assertNotIn("amap-secret", summary)

    def test_serve_runs_only_after_successful_validation(self):
        events = []

        def runner(command, *, cwd):
            events.append(("run", tuple(command)))

        def validator(**kwargs):
            events.append(("validate", kwargs["online_refresh"]))
            return {"district_count": 3}

        def server(project_root):
            events.append(("serve", project_root))

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_baseline_inputs(root)
            self.pipeline.run_pipeline(
                self.pipeline.PipelineOptions(serve=True),
                project_root=root,
                command_runner=runner,
                output_validator=validator,
                server_launcher=server,
            )

        self.assertEqual(events[-2][0], "validate")
        self.assertEqual(events[-1][0], "serve")

    def test_port_8501_conflict_is_reported_without_starting_streamlit(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with self.assertRaisesRegex(
                self.pipeline.PipelineServeError,
                str(port),
            ):
                self.pipeline.ensure_port_available(port)

    def test_summary_records_modes_without_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "pipeline_run_summary.md"
            options = self.pipeline.PipelineOptions(
                refresh_amap=True,
                with_llm=True,
            )
            records = [
                self.pipeline.StageRecord(
                    name="poi",
                    status="completed",
                    duration_seconds=1.25,
                )
            ]
            with patch.dict(
                os.environ,
                {
                    "AMAP_KEY": "amap-secret",
                    "DEEPSEEK_API_KEY": "deepseek-secret",
                },
            ):
                self.pipeline.write_pipeline_summary(
                    path,
                    options=options,
                    records=records,
                    metrics={"active_grid_count": 41},
                )
            content = path.read_text(encoding="utf-8")

        self.assertIn("在线刷新高德：是", content)
        self.assertIn("DeepSeek 报告：是", content)
        self.assertNotIn("amap-secret", content)
        self.assertNotIn("deepseek-secret", content)

    def test_offline_validation_uses_fixed_baseline_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_final_outputs(
                root,
                district_count=3,
                spatial_grid_count=790,
                active_grid_count=41,
            )

            metrics = self.pipeline.validate_pipeline_outputs(
                project_root=root,
                online_refresh=False,
            )

        self.assertEqual(metrics["district_count"], 3)
        self.assertEqual(metrics["spatial_grid_count"], 790)
        self.assertEqual(metrics["active_grid_count"], 41)
        self.assertEqual(metrics["inactive_grid_count"], 19)

    def test_online_validation_accepts_refreshed_spatial_and_activity_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_final_outputs(
                root,
                district_count=3,
                spatial_grid_count=792,
                active_grid_count=43,
            )

            metrics = self.pipeline.validate_pipeline_outputs(
                project_root=root,
                online_refresh=True,
            )

        self.assertEqual(metrics["spatial_grid_count"], 792)
        self.assertEqual(metrics["active_grid_count"], 43)
        self.assertEqual(metrics["inactive_grid_count"], 17)

    def test_validation_reports_repository_relative_output_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_final_outputs(
                root,
                district_count=3,
                spatial_grid_count=790,
                active_grid_count=41,
            )

            metrics = self.pipeline.validate_pipeline_outputs(
                project_root=root,
                online_refresh=False,
            )

        self.assertEqual(
            metrics["convenience_map"],
            "outputs/figures/convenience_grid_map.html",
        )
        self.assertEqual(
            metrics["convenience_report"],
            "outputs/reports/convenience/top_1_选址报告.md",
        )
        self.assertNotIn(str(root), str(metrics))

    def test_validation_requires_market_diagnostic_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_final_outputs(
                root,
                district_count=3,
                spatial_grid_count=790,
                active_grid_count=41,
            )
            score_path = (
                root
                / "outputs"
                / "results"
                / "grid_stage_score_result.csv"
            )
            scores = pd.read_csv(score_path)
            scores = scores.drop(columns=["convenience_market_stage"])
            scores.to_csv(score_path, index=False)

            with self.assertRaisesRegex(
                self.pipeline.PipelineValidationError,
                "convenience_market_stage",
            ):
                self.pipeline.validate_pipeline_outputs(
                    project_root=root,
                    online_refresh=False,
                )

    def _write_baseline_inputs(self, root: Path) -> None:
        processed = root / "data" / "processed"
        processed.mkdir(parents=True)
        pd.DataFrame(
            {
                "district_name": ["云岩区", "南明区", "观山湖区"],
                "adcode": ["520103", "520102", "520115"],
            }
        ).to_csv(processed / "target_districts.csv", index=False)
        (processed / "target_district_boundaries.geojson").write_text(
            '{"type":"FeatureCollection","features":[]}',
            encoding="utf-8",
        )
        pd.DataFrame(
            {
                "grid_id": ["grid_1"],
                "district_name": ["云岩区"],
            }
        ).to_csv(processed / "candidate_grids.csv", index=False)
        pd.DataFrame(
            {
                "grid_id": ["grid_1"],
                "district_name": ["云岩区"],
            }
        ).to_csv(processed / "grid_poi_counts.csv", index=False)
        pd.DataFrame(
            {
                "grid_id": ["grid_1"],
                "district_name": ["云岩区"],
                "category_key": ["convenience_store"],
                "poi_id": ["poi_1"],
            }
        ).to_csv(processed / "grid_poi_raw.csv", index=False)

    def _write_final_outputs(
        self,
        root: Path,
        *,
        district_count: int,
        spatial_grid_count: int,
        active_grid_count: int,
    ) -> None:
        processed = root / "data" / "processed"
        results = root / "outputs" / "results"
        figures = root / "outputs" / "figures"
        reports = root / "outputs" / "reports"
        for path in [processed, results, figures, reports]:
            path.mkdir(parents=True, exist_ok=True)

        districts = ["云岩区", "南明区", "观山湖区"][:district_count]
        pd.DataFrame({"district_name": districts}).to_csv(
            processed / "target_districts.csv",
            index=False,
        )
        pd.DataFrame(
            {
                "grid_id": [
                    f"spatial_{index}" for index in range(spatial_grid_count)
                ],
                "district_name": [
                    districts[index % len(districts)]
                    for index in range(spatial_grid_count)
                ],
            }
        ).to_csv(processed / "candidate_grids.csv", index=False)

        sample_districts = [
            district for district in districts for _ in range(20)
        ]
        grid_ids = [f"grid_{index:03d}" for index in range(60)]
        pd.DataFrame(
            {
                "grid_id": grid_ids,
                "district_name": sample_districts,
            }
        ).to_csv(processed / "grid_poi_counts.csv", index=False)

        active = [index < active_grid_count for index in range(60)]
        scores = pd.DataFrame(
            {
                "grid_id": grid_ids,
                "district_name": sample_districts,
                "has_poi_activity": active,
                "convenience_rank": [
                    index + 1 if value else None
                    for index, value in enumerate(active)
                ],
                "light_food_rank": [
                    index + 1 if value else None
                    for index, value in enumerate(active)
                ],
                "convenience_market_stage": [
                    "一般观察型" if value else "无 POI 活动"
                    for value in active
                ],
                "convenience_competition_alert": [
                    "未触发过度竞争预警" if value else "不参与诊断"
                    for value in active
                ],
                "light_food_market_stage": [
                    "一般观察型" if value else "无 POI 活动"
                    for value in active
                ],
                "light_food_competition_alert": [
                    "未触发过度竞争预警" if value else "不参与诊断"
                    for value in active
                ],
            }
        )
        scores.to_csv(results / "grid_stage_score_result.csv", index=False)

        for name in [
            "convenience_grid_map.html",
            "light_food_grid_map.html",
        ]:
            (figures / name).write_text("<html>map</html>", encoding="utf-8")

        headings = "\n".join(
            f"## 章节 {index}" for index in range(1, 12)
        )
        for profile_id in ["convenience", "light_food"]:
            target = reports / profile_id
            target.mkdir()
            (target / "top_1_选址报告.md").write_text(
                headings,
                encoding="utf-8",
            )


if __name__ == "__main__":
    unittest.main()
