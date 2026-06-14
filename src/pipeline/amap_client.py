"""Amap Web service client with local JSON response caching."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.core.config import get_path


LOGGER = logging.getLogger(__name__)

DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
POI_AROUND_URL = "https://restapi.amap.com/v5/place/around"
POI_POLYGON_URL = "https://restapi.amap.com/v5/place/polygon"


class AmapClient:
    """Small client for Amap district and POI Web service requests."""

    def __init__(self, api_key: str | None = None, cache_dir: str | Path | None = None):
        raw_key = api_key if api_key is not None else os.getenv("AMAP_KEY")
        self.api_key = raw_key.strip() if raw_key else None
        self.demo_mode = not bool(self.api_key)
        self.cache_dir = Path(cache_dir) if cache_dir is not None else get_path("amap_cache_dir")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_district(self, keyword: str, city: str | None = None) -> dict[str, Any] | None:
        """Fetch district metadata and boundary polyline by keyword."""
        if self.demo_mode:
            LOGGER.info("AMAP_KEY 未配置，get_district 使用 demo 模式")
            return None

        params: dict[str, Any] = {
            "key": self.api_key,
            "keywords": keyword,
            "subdistrict": 0,
            "extensions": "all",
            "output": "JSON",
        }
        if city is not None:
            params["city"] = city
        cache_key = self._build_cache_key(DISTRICT_URL, params)
        return self._request_with_cache(DISTRICT_URL, params, cache_key)

    def search_poi_around(
        self,
        location: str,
        keywords: str | None = None,
        radius: int = 500,
        city: str | None = None,
        page: int = 1,
        offset: int = 20,
        types: str | None = None,
    ) -> dict[str, Any] | None:
        """Search POI records around a location."""
        keyword_value = keywords.strip() if keywords else None
        type_value = types.strip() if types else None
        if not keyword_value and not type_value:
            raise ValueError("search_poi_around 要求 keywords 或 types 至少提供一个")
        if self.demo_mode:
            LOGGER.info("AMAP_KEY 未配置，search_poi_around 使用 demo 模式")
            return None

        params: dict[str, Any] = {
            "key": self.api_key,
            "location": location,
            "radius": radius,
            "page_num": page,
            "page_size": offset,
            "output": "JSON",
        }
        if keyword_value:
            params["keywords"] = keyword_value
        if type_value:
            params["types"] = type_value
        if city is not None:
            params["region"] = city
        cache_key = self._build_cache_key(POI_AROUND_URL, params)
        return self._request_with_cache(POI_AROUND_URL, params, cache_key)

    def search_poi_polygon(
        self,
        polygon: str,
        keywords: str,
        city: str | None = None,
        page: int = 1,
        offset: int = 20,
    ) -> dict[str, Any] | None:
        """Search POI records in a polygon."""
        if self.demo_mode:
            LOGGER.info("AMAP_KEY 未配置，search_poi_polygon 使用 demo 模式")
            return None

        params: dict[str, Any] = {
            "key": self.api_key,
            "polygon": polygon,
            "keywords": keywords,
            "page_num": page,
            "page_size": offset,
            "output": "JSON",
        }
        if city is not None:
            params["region"] = city
        cache_key = self._build_cache_key(POI_POLYGON_URL, params)
        return self._request_with_cache(POI_POLYGON_URL, params, cache_key)

    def _build_cache_key(self, url: str, params: dict[str, Any]) -> str:
        """Build a stable JSON cache filename from URL and sorted params."""
        payload = json.dumps({"url": url, "params": params}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{digest}.json"

    def _request_with_cache(
        self,
        url: str,
        params: dict[str, Any],
        cache_key: str,
    ) -> dict[str, Any] | None:
        """Read cached JSON or request Amap and cache the raw JSON response."""
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                LOGGER.warning("缓存文件 JSON 解析失败，将重新请求：%s", cache_path)

        time.sleep(0.2)
        request_url = f"{url}?{urlencode(params)}"
        request = Request(request_url, headers={"User-Agent": "qianzhi-selection/2.0"})
        try:
            with urlopen(request, timeout=15) as response:
                text = response.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("高德请求失败：%s", exc)
            return None

        if not text:
            data: dict[str, Any] = {}
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                LOGGER.warning("高德响应不是合法 JSON：%s", exc)
                return None

        cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
