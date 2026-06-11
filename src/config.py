"""Central project configuration and path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def get_project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


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
    """Return a configured path from v2 `data_paths` or legacy `paths`."""
    cfg = config or load_config()
    data_paths = cfg.get("data_paths", {})
    if key in data_paths:
        return resolve_project_path(data_paths[key])
    paths = cfg.get("paths", {})
    if key not in paths:
        raise KeyError(f"config.yaml 缺少 data_paths.{key} 或 paths.{key}")
    return resolve_project_path(paths[key])


def ensure_dirs(config: dict[str, Any] | None = None) -> None:
    """Create configured v2 data directories and legacy output directories."""
    cfg = config or load_config()
    for value in cfg.get("data_paths", {}).values():
        resolve_project_path(value).mkdir(parents=True, exist_ok=True)

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
        if key in cfg.get("paths", {}):
            get_path(key, cfg).mkdir(parents=True, exist_ok=True)


def ensure_output_dirs(config: dict[str, Any] | None = None) -> None:
    """Backward-compatible alias for directory creation."""
    ensure_dirs(config)


def get_weights(config_or_business_type: dict[str, Any] | str, business_type: str | None = None) -> dict[str, float]:
    """Return v2 weights for a supported business type."""
    if isinstance(config_or_business_type, dict):
        cfg = config_or_business_type
        if business_type is None:
            raise TypeError("get_weights(cfg, business_type) 缺少 business_type")
        key = business_type
    else:
        cfg = load_config()
        key = config_or_business_type

    weights = cfg.get("weights", {})
    if key not in weights:
        raise KeyError(f"config.yaml 缺少 weights.{key}")
    values = weights[key]
    if not isinstance(values, dict):
        raise ValueError(f"config.yaml 中 weights.{key} 必须是映射")
    return dict(values)


def get_poi_categories(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Return configured POI category keywords."""
    cfg = config or load_config()
    categories = cfg.get("poi_categories")
    if not isinstance(categories, dict):
        raise KeyError("config.yaml 缺少 poi_categories")
    return dict(categories)


def get_poi_typecodes(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Return configured Amap POI typecodes for comparison queries."""
    cfg = config or load_config()
    typecodes = cfg.get("poi_typecodes")
    if not isinstance(typecodes, dict):
        raise KeyError("config.yaml 缺少 poi_typecodes")
    return dict(typecodes)
