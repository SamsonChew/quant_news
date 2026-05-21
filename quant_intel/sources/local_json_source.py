from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, normalize_date, stable_hash
from quant_intel.sources.base import Source


class LocalJsonSource(Source):
    name = "Local Social JSON"

    def __init__(self, paths: list[str | Path]) -> None:
        self.paths = [Path(path) for path in paths]

    def fetch(self) -> list[Item]:
        items: list[Item] = []
        for path in self.paths:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError(f"Social JSON must be a list: {path}")
            for record in data:
                if not isinstance(record, dict):
                    continue
                items.append(self._record_to_item(record, path))
        return items

    def _record_to_item(self, record: dict[str, Any], path: Path) -> Item:
        title = clean_text(str(record.get("title", "")))
        url = clean_text(str(record.get("url", "")))
        text = clean_text(str(record.get("text") or record.get("abstract") or ""))
        source = clean_text(str(record.get("source", "Social")))
        source_type = clean_text(str(record.get("source_type", "social"))).lower()
        published = normalize_date(str(record.get("published_at", ""))) or date.today().isoformat()
        authors = record.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        tags = record.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        return Item(
            id=stable_hash([source, source_type, url or title, published]),
            source=source,
            source_type=source_type,
            title=title or text[:80] or "Untitled social item",
            url=url,
            authors=[str(author) for author in authors],
            published_at=published,
            collected_at=utc_now_iso(),
            raw_text=text,
            abstract=text,
            content_hash=stable_hash([url or title, text]),
            tags=[str(tag) for tag in tags],
            metadata={
                "import_path": str(path),
                "likes": record.get("likes", 0),
                "comments": record.get("comments", 0),
                "reposts": record.get("reposts", 0),
            },
        )
