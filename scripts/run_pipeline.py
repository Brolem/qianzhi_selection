"""Run the reproducible v2 delivery pipeline and validate its outputs."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modeling.market_diagnostics import (
    COMPETITION_ALERT,
    INACTIVE_COMPETITION_ALERT,
    INACTIVE_MARKET_STAGE,
    MARKET_STAGE_CULTIVATION,
    MARKET_STAGE_GAP,
    MARKET_STAGE_GENERAL,
    MARKET_STAGE_MATURE,
    NO_COMPETITION_ALERT,
)


SUMMARY_PATH = Path("outputs/results/pipeline_run_summary.md")
TARGET_DISTRICTS = ["云岩区", "南明区", "观山湖区"]
OFFICIAL_RAW_FILES = [
    "宏观经济经济运行-指标数据.xlsx",
    "宏观经济_数据资源数据表.xlsx",
    "宏观经济库目录信息.xlsx",
    "就业表1.xlsx",
    "就业人员信息2.xlsx",
    "就业数据结构.xlsx",
]
BASELINE_INPUTS = {
    "data/processed/target_districts.csv": ["district_name", "adcode"],
    "data/processed/candidate_grids.csv": ["grid_id", "district_name"],
    "data/processed/grid_poi_counts.csv": ["grid_id", "district_name"],
    "data/processed/grid_poi_raw.csv": [
        "grid_id",
        "district_name",
        "category_key",
        "poi_id",
    ],
}


class PipelineError(RuntimeError):
    """Base error raised by the Step 18 pipeline."""


class PipelinePreflightError(PipelineError):
    """Raised before execution when required inputs are unavailable."""


class PipelineExecutionError(PipelineError):
    """Raised when one pipeline stage fails."""


class PipelineValidationError(PipelineError):
    """Raised when generated outputs do not satisfy delivery rules."""


class PipelineServeError(PipelineError):
    """Raised when the Streamlit service cannot start safely."""


@dataclass(frozen=True)
class PipelineOptions:
    """Command-line options controlling optional online stages."""

    refresh_official: bool = False
    refresh_amap: bool = False
    with_llm: bool = False
    serve: bool = False


@dataclass(frozen=True)
class PipelineStage:
    """One sequential subprocess stage."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class StageRecord:
    """Execution result for one completed or failed stage."""

    name: str
    status: str
    duration_seconds: float


CommandRunner = Callable[..., Any]
OutputValidator = Callable[..., dict[str, Any]]
ServerLauncher = Callable[[Path], Any]


def build_stage_commands(
    options: PipelineOptions,
    *,
    python_executable: str | None = None,
) -> list[PipelineStage]:
    """Build the exact module execution order for one pipeline run."""
    python = python_executable or sys.executable
    stages: list[PipelineStage] = []
    if options.refresh_official:
        stages.append(
            PipelineStage(
                "official_data",
                (python, "-m", "src.pipeline.official.official_pipeline"),
            )
        )
    if options.refresh_amap:
        stages.extend(
            [
                PipelineStage(
                    "districts",
                    (python, "-m", "src.pipeline.district_builder"),
                ),
                PipelineStage(
                    "grids",
                    (python, "-m", "src.pipeline.grid_builder"),
                ),
                PipelineStage(
                    "poi",
                    (python, "-m", "src.pipeline.poi_fetcher"),
                ),
            ]
        )
    stages.extend(
        [
            PipelineStage(
                "feature_engineering",
                (python, "-m", "src.modeling.feature_engineering"),
            ),
            PipelineStage(
                "scoring",
                (python, "-m", "src.modeling.scoring_model"),
            ),
            PipelineStage(
                "maps",
                (python, "-m", "src.presentation.map_viz"),
            ),
        ]
    )
    for profile_id in ["convenience", "light_food"]:
        command = [
            python,
            "-m",
            "src.presentation.report_generator",
            "--profile",
            profile_id,
        ]
        if not options.with_llm:
            command.append("--template")
        stages.append(
            PipelineStage(
                f"report_{profile_id}",
                tuple(command),
            )
        )
    return stages


def _require_csv_columns(path: Path, fields: Sequence[str]) -> None:
    try:
        header = pd.read_csv(path, nrows=0).columns.tolist()
    except Exception as exc:
        raise PipelinePreflightError(f"无法读取输入文件：{path}") from exc
    missing = [field for field in fields if field not in header]
    if missing:
        raise PipelinePreflightError(
            f"{path} 缺少字段：" + ", ".join(missing)
        )


def validate_preflight(
    options: PipelineOptions,
    *,
    project_root: str | Path = PROJECT_ROOT,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Validate keys and source files before running any subprocess."""
    root = Path(project_root)
    env = os.environ if environ is None else environ
    if options.refresh_amap and not str(env.get("AMAP_KEY", "")).strip():
        raise PipelinePreflightError(
            "使用 --refresh-amap 前必须配置 AMAP_KEY"
        )
    if options.with_llm and not str(
        env.get("DEEPSEEK_API_KEY", "")
    ).strip():
        raise PipelinePreflightError(
            "使用 --with-llm 前必须配置 DEEPSEEK_API_KEY"
        )
    if options.refresh_official:
        official_dir = root / "data" / "raw" / "official"
        missing = [
            name
            for name in OFFICIAL_RAW_FILES
            if not (official_dir / name).is_file()
        ]
        if missing:
            raise PipelinePreflightError(
                "官方原始数据缺少文件：" + "、".join(missing)
            )
    if options.refresh_amap:
        return
    for relative_path, fields in BASELINE_INPUTS.items():
        path = root / relative_path
        if not path.is_file():
            raise PipelinePreflightError(f"离线基线输入不存在：{path}")
        _require_csv_columns(path, fields)
    boundary_path = (
        root / "data" / "processed" / "target_district_boundaries.geojson"
    )
    if not boundary_path.is_file():
        raise PipelinePreflightError(
            f"离线基线输入不存在：{boundary_path}"
        )
    try:
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelinePreflightError(
            f"无法读取区县边界文件：{boundary_path}"
        ) from exc
    if boundary.get("type") != "FeatureCollection":
        raise PipelinePreflightError(
            f"{boundary_path} 顶层 type 必须为 FeatureCollection"
        )


def _default_command_runner(
    command: Sequence[str],
    *,
    cwd: str | Path,
) -> None:
    subprocess.run(list(command), cwd=cwd, check=True)


def _activity_values(series: pd.Series, path: Path) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false"}).all():
        raise PipelineValidationError(
            f"{path} 中 has_poi_activity 必须为布尔值"
        )
    return normalized.eq("true")


def _read_required_csv(path: Path, fields: Sequence[str]) -> pd.DataFrame:
    if not path.is_file():
        raise PipelineValidationError(f"验收文件不存在：{path}")
    try:
        frame = pd.read_csv(path, dtype={"adcode": str})
    except Exception as exc:
        raise PipelineValidationError(f"无法读取验收文件：{path}") from exc
    missing = [field for field in fields if field not in frame.columns]
    if missing:
        raise PipelineValidationError(
            f"{path} 缺少字段：" + ", ".join(missing)
        )
    return frame


def _validate_report(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise PipelineValidationError(f"报告文件不存在或为空：{path}")
    content = path.read_text(encoding="utf-8")
    heading_count = sum(
        1 for line in content.splitlines() if line.startswith("## ")
    )
    if heading_count != 11:
        raise PipelineValidationError(
            f"{path} 应包含 11 个二级章节，实际为 {heading_count}"
        )


def _relative_display_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise PipelineValidationError(
            f"输出文件不在项目目录内：{path}"
        ) from exc


def validate_pipeline_outputs(
    *,
    project_root: str | Path = PROJECT_ROOT,
    online_refresh: bool = False,
) -> dict[str, Any]:
    """Validate the final data, score, map and report delivery outputs."""
    root = Path(project_root)
    processed = root / "data" / "processed"
    results = root / "outputs" / "results"
    figures = root / "outputs" / "figures"
    reports = root / "outputs" / "reports"

    districts = _read_required_csv(
        processed / "target_districts.csv",
        ["district_name"],
    )
    district_names = districts["district_name"].astype(str).tolist()
    if len(districts) != 3 or set(district_names) != set(TARGET_DISTRICTS):
        raise PipelineValidationError(
            "目标区县必须精确包含云岩区、南明区和观山湖区"
        )

    spatial_grids = _read_required_csv(
        processed / "candidate_grids.csv",
        ["grid_id", "district_name"],
    )
    if spatial_grids["grid_id"].duplicated().any():
        raise PipelineValidationError("空间网格 grid_id 存在重复")
    if not online_refresh and len(spatial_grids) != 790:
        raise PipelineValidationError(
            f"离线基线空间网格应为 790 行，实际为 {len(spatial_grids)} 行"
        )
    if online_refresh and spatial_grids.empty:
        raise PipelineValidationError("在线刷新后空间网格不能为空")

    poi_counts = _read_required_csv(
        processed / "grid_poi_counts.csv",
        ["grid_id", "district_name"],
    )
    if len(poi_counts) != 60:
        raise PipelineValidationError(
            f"POI 样本网格应为 60 行，实际为 {len(poi_counts)} 行"
        )
    poi_district_counts = poi_counts.groupby("district_name").size().to_dict()
    if any(
        int(poi_district_counts.get(district, 0)) != 20
        for district in TARGET_DISTRICTS
    ):
        raise PipelineValidationError("三个目标区县必须各有 20 个 POI 样本网格")

    score_path = results / "grid_stage_score_result.csv"
    scores = _read_required_csv(
        score_path,
        [
            "grid_id",
            "district_name",
            "has_poi_activity",
            "convenience_rank",
            "light_food_rank",
            "convenience_market_stage",
            "convenience_competition_alert",
            "light_food_market_stage",
            "light_food_competition_alert",
        ],
    )
    if len(scores) != 60:
        raise PipelineValidationError(
            f"默认评分结果应为 60 行，实际为 {len(scores)} 行"
        )
    if set(scores["grid_id"].astype(str)) != set(
        poi_counts["grid_id"].astype(str)
    ):
        raise PipelineValidationError("评分结果网格集合与 POI 样本网格不一致")
    activity = _activity_values(scores["has_poi_activity"], score_path)
    active_count = int(activity.sum())
    inactive_count = int((~activity).sum())
    if not online_refresh and (active_count, inactive_count) != (41, 19):
        raise PipelineValidationError(
            "离线基线应包含 41 个活跃网格和 19 个无活动网格"
        )
    if online_refresh and active_count == 0:
        raise PipelineValidationError("在线刷新后至少应有一个活跃网格")
    for rank_field in ["convenience_rank", "light_food_rank"]:
        ranks = pd.to_numeric(scores[rank_field], errors="coerce")
        if ranks.loc[activity].isna().any():
            raise PipelineValidationError(
                f"{score_path} 中活跃网格缺少 {rank_field}"
            )
    market_stages = {
        MARKET_STAGE_GAP,
        MARKET_STAGE_CULTIVATION,
        MARKET_STAGE_MATURE,
        MARKET_STAGE_GENERAL,
    }
    competition_alerts = {
        COMPETITION_ALERT,
        NO_COMPETITION_ALERT,
    }
    for prefix in ["convenience", "light_food"]:
        stage_field = f"{prefix}_market_stage"
        alert_field = f"{prefix}_competition_alert"
        active_stages = set(scores.loc[activity, stage_field].astype(str))
        active_alerts = set(scores.loc[activity, alert_field].astype(str))
        if not active_stages.issubset(market_stages):
            raise PipelineValidationError(
                f"{score_path} 中 {stage_field} 包含无效市场阶段"
            )
        if not active_alerts.issubset(competition_alerts):
            raise PipelineValidationError(
                f"{score_path} 中 {alert_field} 包含无效竞争状态"
            )
        inactive_stages = set(scores.loc[~activity, stage_field].astype(str))
        inactive_alerts = set(scores.loc[~activity, alert_field].astype(str))
        if inactive_stages != {INACTIVE_MARKET_STAGE}:
            raise PipelineValidationError(
                f"{score_path} 中无活动网格的 {stage_field} 必须为"
                f" {INACTIVE_MARKET_STAGE}"
            )
        if inactive_alerts != {INACTIVE_COMPETITION_ALERT}:
            raise PipelineValidationError(
                f"{score_path} 中无活动网格的 {alert_field} 必须为"
                f" {INACTIVE_COMPETITION_ALERT}"
            )

    for map_name in [
        "convenience_grid_map.html",
        "light_food_grid_map.html",
    ]:
        path = figures / map_name
        if not path.is_file() or path.stat().st_size == 0:
            raise PipelineValidationError(f"地图文件不存在或为空：{path}")

    report_paths: dict[str, Path] = {}
    for profile_id, rank_field in [
        ("convenience", "convenience_rank"),
        ("light_food", "light_food_rank"),
    ]:
        ranks = pd.to_numeric(scores[rank_field], errors="coerce")
        top_rows = scores.loc[ranks.eq(1)]
        if len(top_rows) != 1:
            raise PipelineValidationError(
                f"{profile_id} 必须有且仅有一个全局排名第 1 的网格"
            )
        grid_id = str(top_rows.iloc[0]["grid_id"])
        path = reports / profile_id / f"{grid_id}_选址报告.md"
        if not path.exists():
            alternatives = sorted((reports / profile_id).glob("*.md"))
            if len(alternatives) == 1:
                path = alternatives[0]
        _validate_report(path)
        report_paths[profile_id] = path

    return {
        "district_count": len(districts),
        "spatial_grid_count": len(spatial_grids),
        "poi_sample_grid_count": len(poi_counts),
        "active_grid_count": active_count,
        "inactive_grid_count": inactive_count,
        "convenience_map": _relative_display_path(
            figures / "convenience_grid_map.html",
            root,
        ),
        "light_food_map": _relative_display_path(
            figures / "light_food_grid_map.html",
            root,
        ),
        "convenience_report": _relative_display_path(
            report_paths["convenience"],
            root,
        ),
        "light_food_report": _relative_display_path(
            report_paths["light_food"],
            root,
        ),
    }


def write_pipeline_summary(
    path: str | Path,
    *,
    options: PipelineOptions,
    records: Sequence[StageRecord],
    metrics: Mapping[str, Any],
    failure_stage: str | None = None,
    failure_message: str | None = None,
) -> Path:
    """Write a human-readable run summary without credential values."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Step 18 一键运行摘要",
        "",
        "## 运行模式",
        "",
        f"- 重新处理官方数据：{'是' if options.refresh_official else '否'}",
        f"- 在线刷新高德：{'是' if options.refresh_amap else '否'}",
        f"- DeepSeek 报告：{'是' if options.with_llm else '否'}",
        f"- 启动 Streamlit：{'是' if options.serve else '否'}",
        "",
        "## 阶段结果",
        "",
    ]
    if records:
        for record in records:
            lines.append(
                f"- `{record.name}`：{record.status}，"
                f"{record.duration_seconds:.2f} 秒"
            )
    else:
        lines.append("- 尚未执行子流程。")
    if failure_stage is not None:
        lines.extend(
            [
                "",
                "## 失败信息",
                "",
                f"- 失败阶段：`{failure_stage}`",
                f"- 失败原因：{failure_message or '未提供'}",
            ]
        )
    lines.extend(["", "## 验收指标", ""])
    if metrics:
        for key, value in metrics.items():
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 未完成最终验收。")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def ensure_port_available(port: int = 8501) -> None:
    """Ensure the fixed Streamlit port is not already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise PipelineServeError(
                f"端口 {port} 已被占用，不启动重复 Streamlit 服务"
            ) from exc


def launch_streamlit(project_root: Path = PROJECT_ROOT) -> None:
    """Start the workbench on the single fixed delivery port."""
    ensure_port_available(8501)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/app.py",
            "--server.address",
            "0.0.0.0",
            "--server.port",
            "8501",
        ],
        cwd=project_root,
        check=True,
    )


def run_pipeline(
    options: PipelineOptions,
    *,
    project_root: str | Path = PROJECT_ROOT,
    command_runner: CommandRunner = _default_command_runner,
    output_validator: OutputValidator = validate_pipeline_outputs,
    server_launcher: ServerLauncher = launch_streamlit,
) -> dict[str, Any]:
    """Run all selected stages sequentially and validate the final outputs."""
    root = Path(project_root)
    summary_path = root / SUMMARY_PATH
    records: list[StageRecord] = []
    try:
        validate_preflight(options, project_root=root)
    except PipelinePreflightError as exc:
        write_pipeline_summary(
            summary_path,
            options=options,
            records=records,
            metrics={},
            failure_stage="preflight",
            failure_message=str(exc),
        )
        raise

    for stage in build_stage_commands(options):
        print(f"[Step 18] running {stage.name}")
        started = time.perf_counter()
        try:
            command_runner(stage.command, cwd=root)
        except Exception as exc:
            duration = time.perf_counter() - started
            records.append(
                StageRecord(stage.name, "failed", duration)
            )
            write_pipeline_summary(
                summary_path,
                options=options,
                records=records,
                metrics={},
                failure_stage=stage.name,
                failure_message=str(exc),
            )
            raise PipelineExecutionError(
                f"流水线阶段 {stage.name} 执行失败"
            ) from exc
        records.append(
            StageRecord(
                stage.name,
                "completed",
                time.perf_counter() - started,
            )
        )

    try:
        metrics = output_validator(
            project_root=root,
            online_refresh=options.refresh_amap,
        )
    except Exception as exc:
        write_pipeline_summary(
            summary_path,
            options=options,
            records=records,
            metrics={},
            failure_stage="validation",
            failure_message=str(exc),
        )
        if isinstance(exc, PipelineValidationError):
            raise
        raise PipelineValidationError("最终输出验收失败") from exc

    write_pipeline_summary(
        summary_path,
        options=options,
        records=records,
        metrics=metrics,
    )
    print(f"[Step 18] summary: {summary_path}")
    if options.serve:
        server_launcher(root)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    """Build the Step 18 command-line parser."""
    parser = argparse.ArgumentParser(
        description="离线复现或按需在线刷新黔址优选 v2 交付流程。"
    )
    parser.add_argument(
        "--refresh-official",
        action="store_true",
        help="重新处理 data/raw/official 下的六个官方 Excel。",
    )
    parser.add_argument(
        "--refresh-amap",
        action="store_true",
        help="调用高德刷新三区边界、空间网格和60个样本网格。",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="使用 DeepSeek 生成两类 Top 1 报告。",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="验收成功后在 0.0.0.0:8501 启动 Streamlit。",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse CLI arguments and execute the Step 18 pipeline."""
    args = build_parser().parse_args(argv)
    options = PipelineOptions(
        refresh_official=args.refresh_official,
        refresh_amap=args.refresh_amap,
        with_llm=args.with_llm,
        serve=args.serve,
    )
    run_pipeline(options)


if __name__ == "__main__":
    main()
