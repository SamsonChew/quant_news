#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_intel.config import load_report_config, load_scoring_config
from quant_intel.models import Item
from quant_intel.pipeline.classify import classify_item
from quant_intel.pipeline.score import score_item
from quant_intel.pipeline.summarize import summarize_item
from quant_intel.reports import build_daily_report, build_home_dashboard, build_html_dashboard
from quant_intel.reports.crypto_alpha import load_alpha_history
from quant_intel.reports.daily_report import select_history_rows, select_report_rows
from quant_intel.storage import Database


def refresh_existing(
    db_path: Path,
    output_dir: Path,
    report_date: str,
    history_days: int,
) -> int:
    report_day = date.fromisoformat(report_date)
    scoring_config = load_scoring_config()
    report_config = load_report_config()

    db = Database(db_path)
    db.init_schema()
    items = _fetch_items(db.conn)
    updated = 0

    for item in items:
        item = classify_item(item)
        score = score_item(item, scoring_config, today=report_day)
        summary = summarize_item(item, score)
        db.upsert_item(item)
        db.upsert_score(score)
        db.upsert_summary(summary)
        updated += 1

    start_date = (report_day - timedelta(days=history_days - 1)).isoformat()
    history_rows = db.fetch_rows_between(start_date, report_date)
    history_rows = select_history_rows(history_rows, report_config)
    source_stats: dict[str, int] = {}
    for row in history_rows:
        source = str(row.get("source") or "Unknown")
        source_stats[source] = source_stats.get(source, 0) + 1

    today_rows = db.fetch_report_rows(report_date)
    today_selected = select_report_rows(today_rows, report_config)
    today_stats: dict[str, int] = {}
    for row in today_selected:
        source = str(row.get("source") or "Unknown")
        today_stats[source] = today_stats.get(source, 0) + 1
    build_daily_report(
        rows=today_rows,
        report_date=report_date,
        output_dir=output_dir,
        report_config=report_config,
        source_stats=today_stats,
    )
    build_html_dashboard(
        rows=today_rows,
        report_date=report_date,
        output_dir=output_dir,
        report_config=report_config,
        source_stats=today_stats,
    )
    alpha_history = load_alpha_history(output_dir)
    build_home_dashboard(
        rows=history_rows,
        end_date=report_date,
        history_days=history_days,
        output_dir=output_dir,
        report_config=report_config,
        source_stats=source_stats,
        alpha_history=alpha_history,
    )
    db.close()
    return updated


def _fetch_items(conn: sqlite3.Connection) -> list[Item]:
    rows = conn.execute(
        """
        SELECT
          id, source, source_type, title, url, authors, published_at,
          collected_at, raw_text, abstract, content_hash, category, tags,
          language, metadata
        FROM items
        ORDER BY collected_at DESC
        """
    ).fetchall()
    return [_row_to_item(dict(row)) for row in rows]


def _row_to_item(row: dict[str, Any]) -> Item:
    return Item(
        id=str(row["id"]),
        source=str(row["source"]),
        source_type=str(row["source_type"]),
        title=str(row["title"]),
        url=str(row["url"]),
        authors=_json_list(row.get("authors")),
        published_at=str(row.get("published_at") or ""),
        collected_at=str(row.get("collected_at") or ""),
        raw_text=str(row.get("raw_text") or ""),
        abstract=str(row.get("abstract") or ""),
        content_hash=str(row.get("content_hash") or ""),
        category=str(row.get("category") or "Unclassified"),
        tags=_json_list(row.get("tags")),
        language=str(row.get("language") or "en"),
        metadata=_json_dict(row.get("metadata")),
    )


def _json_list(value: Any) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _json_dict(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh existing SQLite items with the current classifier, scorer, and rule summary.",
    )
    parser.add_argument("--db", type=Path, default=Path("data/quant_intel.sqlite"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/daily"))
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--history-days", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    updated = refresh_existing(
        db_path=args.db,
        output_dir=args.output_dir,
        report_date=args.report_date,
        history_days=args.history_days,
    )
    print(f"Refreshed existing items: {updated}")
    print(f"Home: {args.output_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
