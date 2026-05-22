from __future__ import annotations

import gzip
import json
import os
import urllib.request
from datetime import date, datetime, timezone
from typing import Any

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, stable_hash
from quant_intel.sources.base import Source

_BASE = "https://www.zhihu.com/api/v4"

_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "accept-encoding": "gzip",
    "referer": "https://www.zhihu.com/",
    "x-api-version": "3.0.91",
    "authorization": "oauth c3cef7c66a1843f8b3a9e6a1e3160e20",
    "origin": "https://www.zhihu.com",
}


class ZhihuSource(Source):
    name = "知乎"

    def __init__(
        self,
        topics: list[dict[str, str]],
        columns: list[str] | None = None,
        max_results_per_topic: int = 5,
        cookie: str | None = None,
    ) -> None:
        self.topics = topics
        self.columns = columns or []
        self.max_results_per_topic = max_results_per_topic
        self.cookie = cookie or os.environ.get("ZHIHU_COOKIE", "")

    def fetch(self) -> list[Item]:
        if not self.cookie:
            print("[warn] ZhihuSource: ZHIHU_COOKIE not set — skipping 知乎")
            return []

        items: list[Item] = []
        seen: set[str] = set()

        for topic in self.topics:
            label = topic.get("name", topic.get("id", ""))
            try:
                for item in self._fetch_topic(topic):
                    if item.id not in seen:
                        seen.add(item.id)
                        items.append(item)
            except Exception as exc:
                print(f"[warn] ZhihuSource topic '{label}': {exc}")

        for column_id in self.columns:
            try:
                for item in self._fetch_column(column_id):
                    if item.id not in seen:
                        seen.add(item.id)
                        items.append(item)
            except Exception as exc:
                print(f"[warn] ZhihuSource column '{column_id}': {exc}")

        return items

    # ------------------------------------------------------------------

    def _fetch_topic(self, topic: dict[str, str]) -> list[Item]:
        topic_id = topic["id"]
        topic_name = topic.get("name", topic_id)
        url = (
            f"{_BASE}/topics/{topic_id}/feeds/essence"
            f"?after_id=&limit={self.max_results_per_topic}&desktop=true"
        )
        data = self._get_json(url)
        items = []
        for entry in data.get("data", []):
            target = entry.get("target") or entry
            item = self._to_item(target, topic_name)
            if item:
                items.append(item)
        return items

    def _fetch_column(self, column_id: str) -> list[Item]:
        url = f"{_BASE}/columns/{column_id}/items?limit={self.max_results_per_topic}&offset=0"
        data = self._get_json(url)
        items = []
        for entry in data.get("data", []):
            item = self._to_item(entry, column_id)
            if item:
                items.append(item)
        return items

    def _get_json(self, url: str) -> dict[str, Any]:
        headers = {**_HEADERS, "cookie": self.cookie}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", errors="replace"))

    def _to_item(self, target: dict[str, Any], tag: str) -> Item | None:
        t = str(target.get("type", ""))

        if t == "question":
            qid = target.get("id", "")
            title = clean_text(str(target.get("title") or ""))
            excerpt = clean_text(str(target.get("detail") or target.get("excerpt") or ""))
            url = f"https://www.zhihu.com/question/{qid}"
            metadata: dict[str, Any] = {
                "answer_count": target.get("answer_count", 0),
                "follower_count": target.get("follower_count", 0),
            }
            author_obj = target.get("author")

        elif t == "answer":
            question = target.get("question") or {}
            qid = question.get("id", "")
            aid = target.get("id", "")
            title = clean_text(str(question.get("title") or target.get("title") or ""))
            excerpt = clean_text(str(target.get("excerpt") or target.get("content") or ""))
            url = f"https://www.zhihu.com/question/{qid}/answer/{aid}"
            metadata = {"voteup_count": target.get("voteup_count", 0)}
            author_obj = target.get("author")

        elif t == "article":
            aid = target.get("id", "")
            title = clean_text(str(target.get("title") or ""))
            excerpt = clean_text(str(target.get("excerpt") or target.get("content") or ""))
            url = f"https://zhuanlan.zhihu.com/p/{aid}"
            metadata = {"voteup_count": target.get("voteup_count", 0)}
            author_obj = target.get("author")

        else:
            return None

        # Require a non-empty title and a URL that resolves to a real ID
        if not title or not url.rstrip("/").split("/")[-1]:
            return None

        authors: list[str] = []
        if isinstance(author_obj, dict):
            name = clean_text(str(author_obj.get("name", "")))
            if name:
                authors = [name]

        published_at = date.today().isoformat()
        ts = target.get("created") or target.get("created_time")
        if ts:
            try:
                published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        return Item(
            id=stable_hash(["知乎", url]),
            source="知乎",
            source_type="zhihu",
            title=title,
            url=url,
            authors=authors,
            published_at=published_at,
            collected_at=utc_now_iso(),
            raw_text=excerpt,
            abstract=excerpt,
            content_hash=stable_hash([url, excerpt or title]),
            tags=[tag],
            metadata=metadata,
        )
