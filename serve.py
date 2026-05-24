#!/usr/bin/env python3
"""Serve the quant dashboard with a live /feedback endpoint.

Usage:
    python serve.py                      # http://localhost:8080/
    python serve.py --port 9000
    python serve.py --db data/quant_intel.sqlite --output-dir output/daily
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quant_intel.env import load_env_file
from quant_intel.storage import Database


def run(args: argparse.Namespace) -> None:
    load_env_file(args.env_file)
    db = Database(args.db)
    db.init_schema()
    output_dir: Path = args.output_dir

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):  # silence default logging
            pass

        def do_GET(self):
            if self.path.split("?")[0] in ("/", ""):
                path = _latest_dashboard(output_dir)
                if path and path.exists():
                    content = path.read_bytes()
                    self._send(200, "text/html; charset=utf-8", content)
                else:
                    self._send_text(404, "No dashboard found. Run: python run_daily.py")
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

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send(self, code, content_type, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, code, text):
            self._send(code, "text/plain; charset=utf-8", text.encode())

        def _send_json(self, code, obj):
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(obj, ensure_ascii=False).encode(),
            )

    server = HTTPServer(("", args.port), Handler)
    print(f"[serve] http://localhost:{args.port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopped")
    finally:
        db.close()


def _latest_dashboard(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    paths = sorted(output_dir.glob("*.html"), reverse=True)
    return paths[0] if paths else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve quant dashboard + feedback API")
    parser.add_argument("--db", type=Path, default=Path("data/quant_intel.sqlite"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/daily"))
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
