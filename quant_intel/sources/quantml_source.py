from __future__ import annotations

import html
import json
import re
from datetime import date
from urllib.parse import urljoin

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, stable_hash
from quant_intel.sources.base import Source
from quant_intel.sources.http import fetch_text


class QuantMLSource(Source):
    name = "QuantML"

    def __init__(self, url: str = "https://www.quantml.cn/", max_results: int = 8) -> None:
        self.url = url
        self.max_results = max_results

    def fetch(self) -> list[Item]:
        try:
            return self._fetch_papers_json()
        except Exception:
            return self._fetch_homepage_fallback()

    def _fetch_papers_json(self) -> list[Item]:
        raw = fetch_text(urljoin(self.url, "papers.json"))
        payload = json.loads(raw)
        if not isinstance(payload, list):
            return []

        papers = [paper for paper in payload if isinstance(paper, dict)]
        papers.sort(
            key=lambda paper: (
                int(paper.get("year") or 0),
                str(paper.get("processed_date") or ""),
            ),
            reverse=True,
        )
        return [self._paper_to_item(paper) for paper in papers[: self.max_results]]

    def _fetch_homepage_fallback(self) -> list[Item]:
        html_text = fetch_text(self.url)
        text = _html_to_text(html_text)
        titles = _latest_titles(text, self.max_results) or _fallback_titles(text, self.max_results)
        return [self._title_to_item(title) for title in titles]

    def _paper_to_item(self, paper: dict) -> Item:
        title = clean_text(str(paper.get("title") or "Untitled QuantML paper"))
        abstract = clean_text(str(paper.get("abstract") or ""))
        year = int(paper.get("year") or date.today().year)
        authors = paper.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        tags = paper.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        paper_id = clean_text(str(paper.get("id") or title))
        url = f"{urljoin(self.url, 'index.html')}#{paper_id}"
        return Item(
            id=stable_hash([self.name, paper_id]),
            source=self.name,
            source_type="quantml",
            title=title,
            url=url,
            authors=[str(author) for author in authors],
            published_at=f"{year}-01-01",
            collected_at=utc_now_iso(),
            raw_text=abstract,
            abstract=abstract,
            content_hash=stable_hash([title, abstract]),
            tags=[str(tag) for tag in tags],
            metadata={
                "source_url": self.url,
                "quantml_id": paper_id,
                "processed_date": paper.get("processed_date", ""),
            },
        )

    def _title_to_item(self, title: str) -> Item:
        abstract = (
            "QuantML 将金融 AI 论文、主题、模型与策略线索连接成研究图谱，"
            f"当前收录线索包括：{title}。"
        )
        return Item(
            id=stable_hash([self.name, title]),
            source=self.name,
            source_type="quantml",
            title=title,
            url=self.url,
            published_at=_year_from_title(title) or date.today().isoformat(),
            collected_at=utc_now_iso(),
            raw_text=abstract,
            abstract=abstract,
            content_hash=stable_hash([title, abstract]),
            tags=["QuantML", "financial AI", "paper graph"],
            metadata={"source_url": self.url},
        )


def _html_to_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", "\n", value)
    value = html.unescape(value)
    return clean_text(value)


def _latest_titles(text: str, limit: int) -> list[str]:
    marker = "最新收录"
    start = text.find(marker)
    if start == -1:
        return []
    end = text.find("深度研究", start)
    section = text[start:end if end != -1 else None]
    return _year_prefixed_titles(section, limit)


def _fallback_titles(text: str, limit: int) -> list[str]:
    return _year_prefixed_titles(text, limit)


def _year_prefixed_titles(text: str, limit: int) -> list[str]:
    titles: list[str] = []
    pattern = re.compile(r"\b(20\d{2})\s+([^|。；\n]{18,160})")
    for year, raw_title in pattern.findall(text):
        title = clean_text(f"{year} {raw_title}")
        if _looks_like_navigation(title):
            continue
        if title not in titles:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def _year_from_title(title: str) -> str:
    match = re.match(r"(20\d{2})\b", title)
    if not match:
        return ""
    return f"{match.group(1)}-01-01"


def _looks_like_navigation(title: str) -> bool:
    lowered = title.lower()
    return any(
        marker in lowered
        for marker in (
            "copyright",
            "powered by",
            "view all",
            "扫码",
            "加入我们",
        )
    )
