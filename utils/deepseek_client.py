"""
DeepSeek Search / Fetch 客户端
官方独立接口：POST /v1/tools/search 、 POST /v1/tools/fetch
文档：https://api-docs.deepseek.com/ （Search & Fetch）
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient:
    """DeepSeek 联网搜索与网页抓取（与对话 API 共用 API Key）。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or os.getenv("DEEPSEEK_API_KEY") or "").strip()
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def web_search(
        self,
        query: str,
        top_k: int = 8,
        ori_question: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        调用 DeepSeek Search API。

        Returns:
            与项目百度搜索兼容的结构：
            {"references": [...], "provider": "deepseek", "raw": {...}}
        """
        q = (query or "").strip()
        if not q:
            raise ValueError("query 不能为空")
        if not self.available:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法使用 DeepSeek 搜索")

        # API 限制 query 1–128 字符，count 1–50
        q = q[:128]
        count = max(1, min(int(top_k or 8), 50))
        payload: Dict[str, Any] = {"query": q, "count": count}
        if ori_question:
            payload["ori_question"] = str(ori_question)[:512]

        url = f"{self.base_url}/v1/tools/search"
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=self._headers(), json=payload) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"DeepSeek search HTTP {resp.status}: {text[:400]}")
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    import json as _json

                    data = _json.loads(text)

        results = data.get("results") or data.get("data") or []
        references: List[Dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            summary = (
                item.get("summary")
                or item.get("snippet")
                or item.get("content")
                or item.get("text")
                or ""
            )
            references.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or item.get("link") or "",
                    "content": summary,
                    "site_name": item.get("site_name") or "",
                    "date": item.get("date") or "",
                    "authority": item.get("authority"),
                    "rerank_score": item.get("rerank_score"),
                    "image": item.get("image") or item.get("site_icon") or "",
                }
            )

        return {
            "references": references,
            "provider": "deepseek",
            "query": q,
            "count": len(references),
            "raw": data,
        }

    async def fetch(self, url: str) -> Dict[str, Any]:
        """抓取单页，返回 Markdown 正文。"""
        target = (url or "").strip()
        if not target:
            raise ValueError("url 不能为空")
        if not self.available:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法使用 DeepSeek Fetch")

        endpoint = f"{self.base_url}/v1/tools/fetch"
        payload = {"url": target[:8192]}
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, headers=self._headers(), json=payload) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"DeepSeek fetch HTTP {resp.status}: {text[:400]}")
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    import json as _json

                    data = _json.loads(text)

        return {
            "title": data.get("title") or "",
            "content": data.get("content") or data.get("markdown") or data.get("text") or "",
            "url": target,
            "provider": "deepseek",
            "raw": data,
        }


_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client
