"""Central project configuration and path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the project YAML configuration."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件结构无效：{path}")
    return data


def resolve_project_path(value: str | Path) -> Path:
    """Resolve a project-relative path under the project root."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_path(key: str, config: dict[str, Any] | None = None) -> Path:
    """Return a configured path from the top-level `paths` section."""
    cfg = config or load_config()
    paths = cfg.get("paths", {})
    if key not in paths:
        raise KeyError(f"config.yaml 缺少 paths.{key}")
    return resolve_project_path(paths[key])


def ensure_output_dirs(config: dict[str, Any] | None = None) -> None:
    """Create configured output and processed directories."""
    cfg = config or load_config()
    for key in [
        "processed_data",
        "processed_official",
        "processed_osm_region",
        "processed_site_selection",
        "figures",
        "reports",
        "results",
        "results_region_stage",
        "results_grid_stage",
        "results_metadata",
    ]:
        get_path(key, cfg).mkdir(parents=True, exist_ok=True)
