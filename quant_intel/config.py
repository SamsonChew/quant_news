from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_json_config(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    merged = dict(default)
    merged.update(data)
    return merged


def load_sources_config() -> dict[str, Any]:
    return load_json_config(CONFIG_DIR / "sources.json", default={})


def load_scoring_config() -> dict[str, float]:
    default = {
        "relevance_weight": 0.30,
        "novelty_weight": 0.20,
        "academic_weight": 0.15,
        "discussion_weight": 0.15,
        "actionable_weight": 0.20,
    }
    return load_json_config(CONFIG_DIR / "scoring.json", default=default)


def load_report_config() -> dict[str, int]:
    default = {
        "max_items_per_category": 5,
        "max_total_items": 60,
        "executive_brief_items": 5,
    }
    return load_json_config(CONFIG_DIR / "report.json", default=default)
