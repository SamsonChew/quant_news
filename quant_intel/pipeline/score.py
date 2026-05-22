from __future__ import annotations

from datetime import date, datetime
from math import exp, log10

from quant_intel.models import Item, Score, utc_now_iso
from quant_intel.pipeline.classify import CATEGORY_KEYWORDS, _keyword_in_text


def _clamp(value: float) -> float:
    return max(0.0, min(10.0, value))


def _age_days(item: Item, today: date) -> int:
    if not item.published_at:
        return 30
    try:
        published = datetime.fromisoformat(item.published_at[:10]).date()
        return max(0, (today - published).days)
    except ValueError:
        return 30


def score_item(item: Item, weights: dict[str, float], today: date) -> Score:
    text = item.readable_text.lower()
    category_keywords = CATEGORY_KEYWORDS.get(item.category, [])
    keyword_hits = sum(1 for keyword in category_keywords if _keyword_in_text(keyword, text))
    broad_hits = sum(
        1
        for keyword in ("quant", "trading", "finance", "portfolio", "alpha", "risk")
        if _keyword_in_text(keyword, text)
    )

    relevance = _clamp(3.0 + keyword_hits * 1.2 + broad_hits * 0.7)

    age = _age_days(item, today)
    novelty = _clamp(10.0 * exp(-age / 45.0))

    source_academic = {
        "paper": 8.5,
        "blog": 5.5,
        "forum": 4.0,
        "github": 4.5,
        "news": 4.0,
        "social": 4.0,
        "zhihu": 4.5,
        "x": 4.0,
        "quantml": 6.0,
    }.get(item.source_type, 4.0)
    academic = _clamp(source_academic + min(len(item.abstract) / 800.0, 1.5))

    metadata = item.metadata or {}
    stars = float(metadata.get("stars") or 0)
    comments = float(metadata.get("comments") or 0)
    likes = float(metadata.get("likes") or 0)
    reposts = float(metadata.get("reposts") or 0)
    discussion_base = 2.0
    if item.source_type == "github":
        discussion = discussion_base + min(log10(stars + 1) * 2.5, 6.0)
    elif item.source_type == "forum":
        discussion = discussion_base + min(log10(comments + 1) * 3.0, 5.0) + 1.0
    elif item.source_type in {"social", "zhihu", "x"}:
        social_activity = likes + comments * 2.0 + reposts * 3.0
        discussion = discussion_base + min(log10(social_activity + 1) * 2.2, 6.0)
    else:
        discussion = discussion_base + (1.0 if metadata.get("linked_discussion") else 0.0)
    discussion = _clamp(discussion)

    actionable_categories = {
        "Alpha / Factor Research",
        "Statistical Arbitrage",
        "Portfolio Construction",
        "Execution / Transaction Cost",
        "Backtesting / Research Tools",
        "Data Engineering",
        "LLM / Agents for Quant",
        "Machine Learning for Finance",
    }
    actionable = 4.5
    if item.category in actionable_categories:
        actionable += 2.0
    if item.category == "Industry / Career":
        actionable -= 1.5
    if item.source_type == "github":
        actionable += 1.5
    if any(_keyword_in_text(keyword, text) for keyword in ("code", "dataset", "implementation", "backtest")):
        actionable += 1.0
    actionable = _clamp(actionable)

    final = (
        weights["relevance_weight"] * relevance
        + weights["novelty_weight"] * novelty
        + weights["academic_weight"] * academic
        + weights["discussion_weight"] * discussion
        + weights["actionable_weight"] * actionable
    )

    return Score(
        item_id=item.id,
        relevance_score=round(relevance, 3),
        novelty_score=round(novelty, 3),
        academic_score=round(academic, 3),
        discussion_score=round(discussion, 3),
        actionable_score=round(actionable, 3),
        final_score=round(final, 3),
        created_at=utc_now_iso(),
    )
