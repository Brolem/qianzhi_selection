"""Central project configuration and path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
    """Return a configured current-project path from `data_paths`."""
    cfg = config or load_config()
    data_paths = cfg.get("data_paths", {})
    if key not in data_paths:
        raise KeyError(f"config.yaml 缺少 data_paths.{key}")
    return resolve_project_path(data_paths[key])


def ensure_dirs(config: dict[str, Any] | None = None) -> None:
    """Create all configured current-project data directories."""
    cfg = config or load_config()
    for value in cfg.get("data_paths", {}).values():
        resolve_project_path(value).mkdir(parents=True, exist_ok=True)


def ensure_output_dirs(config: dict[str, Any] | None = None) -> None:
    """Create configured current-project directories."""
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


def get_scoring_templates(config: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    """Return configured Step 8 scoring template field mappings."""
    cfg = config or load_config()
    templates = cfg.get("scoring_templates")
    if not isinstance(templates, dict):
        raise KeyError("config.yaml 缺少 scoring_templates")

    result: dict[str, dict[str, str]] = {}
    for template_id, values in templates.items():
        if not isinstance(values, dict):
            raise ValueError(
                f"config.yaml 中 scoring_templates.{template_id} 必须是映射"
            )
        result[str(template_id)] = dict(values)
    return result


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


def get_amap_map_config(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return validated non-sensitive Amap JS rendering settings."""
    cfg = config or load_config()
    values = cfg.get("map")
    if not isinstance(values, dict):
        raise KeyError("config.yaml 缺少 map")
    required = [
        "provider",
        "js_api_version",
        "map_style",
        "default_zoom",
        "height",
        "top_n",
        "enable_folium_fallback",
    ]
    missing = [field for field in required if field not in values]
    if missing:
        raise KeyError("config.yaml 缺少 map." + ", map.".join(missing))
    result = {field: values[field] for field in required}
    if result["provider"] != "amap_js":
        raise ValueError("config.yaml 中 map.provider 必须为 amap_js")
    if str(result["js_api_version"]) != "2.0":
        raise ValueError("config.yaml 中 map.js_api_version 必须为 2.0")
    for field in ["default_zoom", "height", "top_n"]:
        if isinstance(result[field], bool) or not isinstance(result[field], int):
            raise ValueError(f"config.yaml 中 map.{field} 必须为整数")
        if result[field] <= 0:
            raise ValueError(f"config.yaml 中 map.{field} 必须大于 0")
    if not isinstance(result["map_style"], str) or not result["map_style"]:
        raise ValueError("config.yaml 中 map.map_style 必须为非空文本")
    if not isinstance(result["enable_folium_fallback"], bool):
        raise ValueError(
            "config.yaml 中 map.enable_folium_fallback 必须为布尔值"
        )
    return result
