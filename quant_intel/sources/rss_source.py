from __future__ import annotations

from datetime import date
from xml.etree import ElementTree as ET

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, normalize_date, stable_hash
from quant_intel.sources.base import Source
from quant_intel.sources.http import fetch_text


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class RSSSource(Source):
    name = "RSS"

    def __init__(self, feeds: list[dict], max_results_per_feed: int = 10) -> None:
        self.feeds = feeds
        self.max_results_per_feed = max_results_per_feed

    def fetch(self) -> list[Item]:
        items: list[Item] = []
        for feed in self.feeds:
            try:
                xml_text = fetch_text(feed["url"])
                parsed = self._parse_feed(xml_text, feed)
            except Exception as exc:
                print(f"[warn] RSS feed failed: {feed['name']}: {exc}")
                continue
            items.extend(parsed[: self.max_results_per_feed])
        return items

    def _parse_feed(self, xml_text: str, feed: dict) -> list[Item]:
        root = ET.fromstring(xml_text)
        if root.tag.endswith("feed"):
            return self._parse_atom(root, feed)
        return self._parse_rss(root, feed)

    def _parse_atom(self, root: ET.Element, feed: dict) -> list[Item]:
        items: list[Item] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            title = clean_text(_text(entry, "atom:title"))
            url = _atom_link(entry)
            summary = clean_text(_text(entry, "atom:summary") or _text(entry, "atom:content"))
            published = normalize_date(
                _text(entry, "atom:published") or _text(entry, "atom:updated")
            )
            author = clean_text(_text(entry, "atom:author/atom:name"))
            items.append(
                Item(
                    id=stable_hash([feed["name"], url or title]),
                    source=feed["name"],
                    source_type=feed.get("source_type", "blog"),
                    title=title,
                    url=url,
                    authors=[author] if author else [],
                    published_at=published or date.today().isoformat(),
                    collected_at=utc_now_iso(),
                    raw_text=summary,
                    abstract=summary,
                    content_hash=stable_hash([title, summary]),
                    metadata={"feed_url": feed["url"]},
                )
            )
        return items

    def _parse_rss(self, root: ET.Element, feed: dict) -> list[Item]:
        channel = root.find("channel")
        if channel is None:
            return []
        items: list[Item] = []
        for entry in channel.findall("item"):
            title = clean_text(_child_text(entry, "title"))
            url = clean_text(_child_text(entry, "link"))
            summary = clean_text(
                _child_text(entry, "description") or _child_text(entry, "summary")
            )
            published = normalize_date(_child_text(entry, "pubDate"))
            author = clean_text(_child_text(entry, "author"))
            items.append(
                Item(
                    id=stable_hash([feed["name"], url or title]),
                    source=feed["name"],
                    source_type=feed.get("source_type", "blog"),
                    title=title,
                    url=url,
                    authors=[author] if author else [],
                    published_at=published or date.today().isoformat(),
                    collected_at=utc_now_iso(),
                    raw_text=summary,
                    abstract=summary,
                    content_hash=stable_hash([title, summary]),
                    metadata={"feed_url": feed["url"]},
                )
            )
        return items


def _text(parent: ET.Element, path: str) -> str:
    child = parent.find(path, ATOM_NS)
    return child.text if child is not None and child.text else ""


def _child_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    return child.text if child is not None and child.text else ""


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        href = link.attrib.get("href")
        if href and link.attrib.get("rel", "alternate") == "alternate":
            return href
    first = entry.find("atom:link", ATOM_NS)
    return first.attrib.get("href", "") if first is not None else ""
