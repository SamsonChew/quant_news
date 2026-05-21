from __future__ import annotations

import time
from datetime import date
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, normalize_date, stable_hash
from quant_intel.sources.base import Source
from quant_intel.sources.http import fetch_text


ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSource(Source):
    name = "arXiv"

    def __init__(
        self, queries: list[str], max_results: int = 15, delay_seconds: float = 3.2
    ) -> None:
        self.queries = queries
        self.max_results = max_results
        self.delay_seconds = delay_seconds

    def fetch(self) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()
        for index, query in enumerate(self.queries):
            params = urlencode(
                {
                    "search_query": query,
                    "start": 0,
                    "max_results": self.max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
            )
            try:
                xml_text = fetch_text(f"{ARXIV_API}?{params}")
                root = ET.fromstring(xml_text)
            except Exception as exc:
                print(f"[warn] arXiv query failed: {query}: {exc}")
                continue
            for entry in root.findall("atom:entry", ATOM_NS):
                item = self._entry_to_item(entry)
                if item.id in seen:
                    continue
                seen.add(item.id)
                items.append(item)
            if index < len(self.queries) - 1:
                time.sleep(self.delay_seconds)
        return items

    def _entry_to_item(self, entry: ET.Element) -> Item:
        arxiv_id = clean_text(_text(entry, "atom:id"))
        title = clean_text(_text(entry, "atom:title"))
        abstract = clean_text(_text(entry, "atom:summary"))
        published = normalize_date(_text(entry, "atom:published"))
        authors = [
            clean_text(_text(author, "atom:name"))
            for author in entry.findall("atom:author", ATOM_NS)
        ]
        categories = [
            category.attrib.get("term", "")
            for category in entry.findall("atom:category", ATOM_NS)
            if category.attrib.get("term")
        ]
        item_hash = stable_hash([arxiv_id or title, abstract])
        return Item(
            id=stable_hash(["arxiv", arxiv_id or title]),
            source=self.name,
            source_type="paper",
            title=title,
            url=arxiv_id,
            authors=authors,
            published_at=published or date.today().isoformat(),
            collected_at=utc_now_iso(),
            raw_text=abstract,
            abstract=abstract,
            content_hash=item_hash,
            tags=categories,
            metadata={"arxiv_categories": categories},
        )


def _text(parent: ET.Element, path: str) -> str:
    child = parent.find(path, ATOM_NS)
    return child.text if child is not None and child.text else ""
