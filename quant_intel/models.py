from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Item:
    id: str
    source: str
    source_type: str
    title: str
    url: str
    authors: list[str] = field(default_factory=list)
    published_at: str = ""
    collected_at: str = ""
    raw_text: str = ""
    abstract: str = ""
    content_hash: str = ""
    category: str = "Unclassified"
    tags: list[str] = field(default_factory=list)
    language: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def readable_text(self) -> str:
        parts = [self.title, self.abstract, self.raw_text]
        return "\n".join(part for part in parts if part).strip()


@dataclass(slots=True)
class Summary:
    item_id: str
    one_line_summary: str
    technical_summary: str
    key_points: list[str]
    quant_relevance: str
    possible_use_case: str
    limitations: str
    read_priority: str
    model_name: str = "rule_based_v0"
    created_at: str = ""
    key_figures_md: str = ""
    prompt_version: str = ""


@dataclass(slots=True)
class Score:
    item_id: str
    relevance_score: float
    novelty_score: float
    academic_score: float
    discussion_score: float
    actionable_score: float
    final_score: float
    created_at: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
