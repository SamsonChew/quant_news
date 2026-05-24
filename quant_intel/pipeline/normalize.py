from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable


SPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = TAG_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def stable_hash(parts: Iterable[str]) -> str:
    joined = "\n".join(part.strip().lower() for part in parts if part and part.strip())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def normalize_date(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(raw)
        return parsed.date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return raw[:10]


def truncate(value: str, limit: int) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def canonical_url(url: str) -> str:
    """Normalise a URL so the same content from different sources compares equal.

    Currently handles arXiv: strips /pdf/ vs /abs/ difference and version suffixes (v1, v2 …).
    For all other URLs returns the URL lowercased and stripped.
    """
    if not url:
        return ""
    # arXiv: normalise to https://arxiv.org/abs/{id} without version suffix
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d+)(?:v\d+)?", url)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"
    return url.lower().strip()
