from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable

_STOP_WORDS = frozenset(
    "a an the and or in on of to for with is are was were be been "
    "this that these those it its using via from by at".split()
)


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


_TRACKING_PARAMS = re.compile(
    r"(?:^|&)(?:utm_\w+|ref|fbclid|gclid|mc_\w+|source|medium|campaign|"
    r"from|via|share|si|feature|app)=[^&]*",
    re.IGNORECASE,
)

def canonical_url(url: str) -> str:
    """Normalise a URL so the same content from different sources compares equal."""
    if not url:
        return ""

    # arXiv: normalise to https://arxiv.org/abs/{id} without version suffix
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d+)(?:v\d+)?", url)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"

    # GitHub: strip tree/blob/commit path segments so repo root == any branch view
    m = re.match(r"(https?://github\.com/[^/]+/[^/]+)(?:/(?:tree|blob|commit)/[^\?#]*)?", url, re.IGNORECASE)
    if m:
        return m.group(1).lower().rstrip("/")

    # General: strip fragment, strip tracking query params, lowercase, strip trailing slash
    url = url.lower().strip()
    if "#" in url:
        url = url[: url.index("#")]
    if "?" in url:
        base, qs = url.split("?", 1)
        qs = _TRACKING_PARAMS.sub("", qs).strip("&")
        url = f"{base}?{qs}" if qs else base
    return url.rstrip("/")


def title_tokens(title: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return frozenset(w for w in words if w not in _STOP_WORDS and len(w) > 1)


def title_jaccard(a: str, b: str) -> float:
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def dedup_by_title(items: list, score_key: str = "final_score", threshold: float = 0.72) -> list:
    """Remove near-duplicate titles, keeping the higher-scored item."""
    kept: list = []
    for item in sorted(items, key=lambda x: x.get(score_key, 0) if isinstance(x, dict) else getattr(x, score_key, 0), reverse=True):
        title = item.get("title", "") if isinstance(item, dict) else getattr(item, "title", "")
        is_dup = any(
            title_jaccard(title, (k.get("title", "") if isinstance(k, dict) else getattr(k, "title", ""))) >= threshold
            for k in kept
        )
        if not is_dup:
            kept.append(item)
    return kept
