#!/usr/bin/env python3
"""Generate static JSON files for GitHub Pages deployment.

Writes output/daily/api/summary.json, items.json, alpha.json
so the dashboard works without a live serve.py backend.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from quant_intel.config import load_report_config
from quant_intel.env import load_env_file
from quant_intel.i18n import CATEGORY_ZH, PRIORITY_ZH, SOURCE_TYPE_ZH
from quant_intel.reports.crypto_alpha import load_alpha_history
from quant_intel.reports.daily_report import select_report_rows, select_history_rows
from quant_intel.reports.home_dashboard import _with_display_labels, build_home_dashboard
from quant_intel.reports.sections import REPORT_SECTIONS
from quant_intel.storage import Database


def build_static(
    db_path: Path = Path("data/quant_intel.sqlite"),
    output_dir: Path = Path("output/daily"),
    history_days: int = 7,
) -> None:
    load_env_file(Path(".env"))
    db = Database(db_path)
    db.init_schema()
    report_config = load_report_config()

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=history_days - 1)).isoformat()

    # ── summary.json ──────────────────────────────────────────────────────────
    raw_days = db.get_days_with_counts(start, end)
    days = []
    for day_info in raw_days:
        d = day_info["date"]
        raw = db.fetch_rows_between(d, d)
        filtered = select_report_rows(raw, report_config)
        days.append({"date": d, "count": len(filtered)})

    cat_counts = db.get_category_counts_between(start, end)
    source_stats = db.source_stats_between(start, end)

    summary = {
        "days": days,
        "sections": [
            {"key": s.key, "label": s.label, "description": s.description}
            for s in REPORT_SECTIONS
        ],
        "category_labels": CATEGORY_ZH,
        "priority_labels": PRIORITY_ZH,
        "source_type_labels": SOURCE_TYPE_ZH,
        "category_counts": cat_counts,
        "source_stats": source_stats,
        "history_days": history_days,
        "end_date": end,
    }

    # ── items.json ────────────────────────────────────────────────────────────
    raw_all = db.fetch_rows_between(start, end)
    rows = select_history_rows(raw_all, report_config)
    enriched = [_with_display_labels(row) for row in rows]

    # ── alpha.json ────────────────────────────────────────────────────────────
    alpha_history = load_alpha_history(output_dir)

    # ── Write files ───────────────────────────────────────────────────────────
    api_dir = output_dir / "api"
    api_dir.mkdir(parents=True, exist_ok=True)

    (api_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (api_dir / "items.json").write_text(
        json.dumps({"items": enriched, "total": len(enriched)}, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    (api_dir / "alpha.json").write_text(
        json.dumps({"history": alpha_history}, ensure_ascii=False, default=str), encoding="utf-8"
    )

    db.close()

    # ── Regenerate index.html with updated JS ─────────────────────────────────
    history_rows = db.conn.close() or None  # already closed above
    db2 = Database(db_path)
    history_raw = db2.fetch_rows_between(start, end)
    history_rows = select_history_rows(history_raw, report_config)
    history_stats = dict(Counter(str(r.get("source", "")) for r in history_rows))

    from quant_intel.notes.reader import load_notes
    from quant_intel.reports.weekly_loader import load_weekly_reports
    notes = load_notes(Path("notes"))
    weekly = load_weekly_reports(Path("/Users/samsonchew/Desktop/Quant/weekly_report"))

    build_home_dashboard(
        rows=history_rows,
        end_date=end,
        history_days=history_days,
        output_dir=output_dir,
        report_config=report_config,
        source_stats=history_stats,
        alpha_history=alpha_history,
        notes=notes,
        weekly_reports=weekly,
    )
    db2.close()

    print(f"[static] api/summary.json  — {len(days)} days")
    print(f"[static] api/items.json    — {len(enriched)} items")
    print(f"[static] api/alpha.json    — {len(alpha_history)} entries")
    print(f"[static] index.html regenerated")


if __name__ == "__main__":
    build_static()
