#!/usr/bin/env python3
"""Serve the quant dashboard with a live REST API.

Endpoints:
    GET  /                   → lean index.html shell
    GET  /api/summary        → days list, sections, category counts
    GET  /api/items          → paginated items (date, section, category, q, offset, limit)
    GET  /api/alpha          → crypto alpha history
    POST /feedback           → upsert feedback signal {id, signal}
    GET  /*.html             → static daily report files
    GET  /*.json             → static JSON files

Usage:
    python serve.py [--port 8080] [--db data/quant_intel.sqlite] [--history-days 7]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent))

from quant_intel.env import load_env_file
from quant_intel.i18n import CATEGORY_ZH, PRIORITY_ZH, SOURCE_TYPE_ZH
from quant_intel.config import load_report_config
from quant_intel.reports.crypto_alpha import load_alpha_history
from quant_intel.reports.daily_report import select_report_rows, select_history_rows
from quant_intel.reports.home_dashboard import _with_display_labels
from quant_intel.reports.sections import REPORT_SECTIONS
from quant_intel.storage import Database

_REPORT_CONFIG = load_report_config()


def _text_matches(row: dict, q: str) -> bool:
    text = " ".join(
        str(row.get(f) or "")
        for f in (
            "title", "display_title", "one_line_summary", "technical_summary",
            "tldr", "core_value", "source", "category", "source_type",
        )
    ).lower()
    return q in text


def run(args: argparse.Namespace) -> None:
    load_env_file(args.env_file)
    db = Database(args.db)
    db.init_schema()
    output_dir: Path = args.output_dir
    history_days: int = args.history_days

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            params = {k: v[-1] for k, v in parse_qs(parsed.query).items()}

            if path == "/" or path == "/index.html":
                self._serve_shell(output_dir)
            elif path == "/api/summary":
                self._api_summary(db, history_days)
            elif path == "/api/items":
                self._api_items(db, params, history_days)
            elif path == "/api/alpha":
                self._api_alpha(output_dir)
            elif path.endswith((".html", ".json")):
                self._serve_static(output_dir, path.lstrip("/"))
            else:
                self._send_text(404, "Not found")

        def do_POST(self):
            if self.path == "/feedback":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    item_id = str(data.get("id", "")).strip()
                    signal = int(data.get("signal", 0))
                    if item_id and signal in (-1, 0, 1):
                        db.upsert_feedback(item_id, signal)
                        label = {1: "👍 有用", -1: "👎 跳过", 0: "取消"}[signal]
                        print(f"[feedback] {item_id[:20]}… {label}")
                    self._send_json(200, {"ok": True})
                except Exception as exc:
                    self._send_json(400, {"error": str(exc)})
            else:
                self._send_text(404, "Not found")

        def do_OPTIONS(self):
            self.send_response(200)
            self._cors()
            self.end_headers()

        # ── API handlers ──────────────────────────────────────────────────────

        def _api_summary(self, db: Database, history_days: int) -> None:
            end = date.today().isoformat()
            start = (date.today() - timedelta(days=history_days - 1)).isoformat()
            raw_days = db.get_days_with_counts(start, end)
            # Compute filtered count per day (matches what /api/items returns)
            days = []
            for day_info in raw_days:
                d = day_info["date"]
                raw = db.fetch_rows_between(d, d)
                filtered = select_report_rows(raw, _REPORT_CONFIG)
                days.append({"date": d, "count": len(filtered)})
            cat_counts = db.get_category_counts_between(start, end)
            source_stats = db.source_stats_between(start, end)
            self._send_json(200, {
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
            })

        def _api_items(self, db: Database, params: dict, history_days: int) -> None:
            req_date = params.get("date", "")
            section = params.get("section", "All")
            category = params.get("category", "All")
            q = params.get("q", "").lower().strip()
            offset = max(0, int(params.get("offset", 0)))
            limit = min(max(1, int(params.get("limit", 30))), 200)

            if req_date:
                raw = db.fetch_rows_between(req_date, req_date)
                rows = select_report_rows(raw, _REPORT_CONFIG)
            else:
                end = date.today().isoformat()
                start = (date.today() - timedelta(days=history_days - 1)).isoformat()
                raw = db.fetch_rows_between(start, end)
                # Apply per-day selection so every day gets fair representation
                rows = select_history_rows(raw, _REPORT_CONFIG)
            enriched = [_with_display_labels(row) for row in rows]

            if section != "All":
                enriched = [r for r in enriched if section in (r.get("report_sections") or [])]
            if category != "All":
                enriched = [r for r in enriched if r.get("category") == category]
            if q:
                enriched = [r for r in enriched if _text_matches(r, q)]

            total = len(enriched)
            page = enriched[offset: offset + limit]
            self._send_json(200, {"items": page, "total": total, "offset": offset, "limit": limit})

        def _api_alpha(self, output_dir: Path) -> None:
            history = load_alpha_history(output_dir)
            self._send_json(200, {"history": history})

        # ── Static file serving ───────────────────────────────────────────────

        def _serve_shell(self, output_dir: Path) -> None:
            index = output_dir / "index.html"
            if index.exists():
                self._send(200, "text/html; charset=utf-8", index.read_bytes())
            else:
                self._send_text(404, "Dashboard not found. Run: python run_daily.py")

        def _serve_static(self, output_dir: Path, rel: str) -> None:
            file_path = output_dir / rel
            if file_path.exists() and file_path.is_file():
                ct = "text/html; charset=utf-8" if rel.endswith(".html") else "application/json"
                self._send(200, ct, file_path.read_bytes())
            else:
                self._send_text(404, f"Not found: {rel}")

        # ── Low-level helpers ─────────────────────────────────────────────────

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send(self, code: int, content_type: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, code: int, text: str) -> None:
            self._send(code, "text/plain; charset=utf-8", text.encode())

        def _send_json(self, code: int, obj: object) -> None:
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(obj, ensure_ascii=False, default=str).encode(),
            )

    server = HTTPServer(("", args.port), Handler)
    print(f"[serve] http://localhost:{args.port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopped")
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve quant dashboard + REST API")
    parser.add_argument("--db", type=Path, default=Path("data/quant_intel.sqlite"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/daily"))
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--history-days", type=int, default=7)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
