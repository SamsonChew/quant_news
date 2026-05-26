from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_intel.i18n import CATEGORY_ZH, PRIORITY_ZH, SOURCE_TYPE_ZH
from quant_intel.i18n import category_zh, priority_zh, source_type_zh
from quant_intel.models import utc_now_iso
from quant_intel.reports.reader_format import with_reader_format
from quant_intel.reports.sections import REPORT_SECTIONS
from quant_intel.reports.sections import row_section_keys, row_section_labels, section_counts


def build_home_dashboard(
    rows: list[dict[str, Any]],
    end_date: str,
    history_days: int,
    output_dir: Path,
    report_config: dict[str, int],
    source_stats: dict[str, int],
    alpha_history: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
    weekly_reports: list[dict[str, Any]] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = [_with_display_labels(row) for row in rows]
    payload = {
        "end_date": end_date,
        "history_days": history_days,
        "generated_at": utc_now_iso(),
        "items": enriched,
        "source_stats": source_stats,
        "report_config": report_config,
        "day_counts": dict(Counter(_day(row) for row in enriched)),
        "section_counts": _section_counts_from_field(enriched),
        "category_counts": dict(Counter(row["category"] for row in enriched)),
        "sections": [
            {
                "key": section.key,
                "label": section.label,
                "description": section.description,
            }
            for section in REPORT_SECTIONS
        ],
        "category_labels": CATEGORY_ZH,
        "priority_labels": PRIORITY_ZH,
        "source_type_labels": SOURCE_TYPE_ZH,
        "alpha_history": alpha_history or [],
        "notes": notes or [],
        "weekly_reports": weekly_reports or [],
    }
    path = output_dir / "index.html"
    path.write_text(_render_home(payload), encoding="utf-8")
    return path


def _render_home(payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>samson 量化情报台</title>
  <style>
    :root {{
      --bg: #ffffff;
      --panel: #ffffff;
      --ink: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --blue: #1a73e8;
      --red: #ea4335;
      --yellow: #fbbc04;
      --green: #34a853;
      --blue-soft: #e8f0fe;
      --green-soft: #e6f4ea;
      --yellow-soft: #fef7e0;
      --red-soft: #fce8e6;
      --radius: 16px;
      --shadow: 0 1px 2px rgba(60, 64, 67, 0.16), 0 8px 24px rgba(60, 64, 67, 0.10);
      --topbar-h: 108px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(66, 133, 244, 0.07), transparent 30%),
        radial-gradient(circle at top right, rgba(251, 188, 4, 0.08), transparent 26%),
        var(--bg);
      color: var(--ink);
      font-family: "Google Sans", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}

    button, input, select {{ font: inherit; }}

    /* ── Topbar ──────────────────────────────────────────────────────────────── */
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(18px);
      border-bottom: 1px solid var(--line);
    }}

    .topbar-main {{
      display: grid;
      grid-template-columns: minmax(200px, 1fr) minmax(280px, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 12px 32px 8px;
    }}

    .brand h1 {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 0;
      color: var(--ink);
      font-size: 23px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}

    .brand h1::before {{
      content: "";
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: conic-gradient(from 0deg, var(--blue) 0 25%, var(--red) 0 50%, var(--yellow) 0 75%, var(--green) 0 100%);
      box-shadow: inset 0 0 0 6px #fff;
      flex-shrink: 0;
    }}

    .brand p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 12px;
    }}

    .controls {{
      display: grid;
      grid-template-columns: 1fr 130px 140px 140px;
      gap: 8px;
      align-items: center;
    }}

    .control {{
      height: 40px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--ink);
      padding: 0 14px;
      outline: none;
    }}

    .control:focus {{
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.14);
    }}

    /* ── Tab bar ─────────────────────────────────────────────────────────────── */
    .tab-row {{
      display: flex;
      gap: 0;
      padding: 0 28px;
    }}

    .tab-btn {{
      height: 38px;
      padding: 0 20px;
      border: none;
      border-bottom: 3px solid transparent;
      background: transparent;
      color: var(--muted);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: color 120ms, border-color 120ms;
      white-space: nowrap;
    }}

    .tab-btn.active {{
      color: var(--blue);
      border-bottom-color: var(--blue);
    }}

    .tab-btn:hover:not(.active) {{
      color: var(--ink);
    }}

    .tab-panel.hidden {{
      display: none;
    }}

    /* ── Intel tab layout ────────────────────────────────────────────────────── */
    .layout {{
      display: grid;
      grid-template-columns: 280px minmax(440px, 1fr);
      gap: 22px;
      padding: 24px 32px 36px;
    }}

    .rail {{
      position: sticky;
      top: var(--topbar-h);
      height: calc(100vh - var(--topbar-h) - 16px);
      overflow: auto;
    }}

    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 16px;
    }}

    .metric {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      padding: 12px;
      box-shadow: 0 1px 2px rgba(60, 64, 67, 0.08);
    }}

    .metric:nth-child(1) {{ border-top: 3px solid var(--blue); }}
    .metric:nth-child(2) {{ border-top: 3px solid var(--red); }}
    .metric:nth-child(3) {{ border-top: 3px solid var(--yellow); }}
    .metric:nth-child(4) {{ border-top: 3px solid var(--green); }}

    .metric b {{
      display: block;
      font-size: 22px;
      line-height: 1;
      color: var(--ink);
    }}

    .metric span {{
      display: block;
      margin-top: 7px;
      color: var(--muted);
      font-size: 12px;
    }}

    .section-label {{
      margin: 18px 0 8px;
      color: var(--blue);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.02em;
    }}

    .nav-list {{
      display: grid;
      gap: 7px;
    }}

    .nav-button {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      width: 100%;
      min-height: 38px;
      border: 1px solid transparent;
      border-radius: 999px;
      background: transparent;
      color: var(--ink);
      padding: 8px 10px;
      text-align: left;
      cursor: pointer;
    }}

    .nav-button:hover,
    .nav-button.active {{
      border-color: transparent;
      background: var(--blue-soft);
      color: #174ea6;
    }}

    .count {{
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}

    .source-list {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}

    .source-list li {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
    }}

    .feed-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      margin-bottom: 12px;
    }}

    .feed-head h2 {{
      margin: 0;
      font-size: 19px;
    }}

    .feed-head span {{
      color: var(--muted);
      font-size: 13px;
    }}

    .day-group {{
      margin-bottom: 28px;
    }}

    .day-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin: 0 0 14px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 10px;
    }}

    .day-title h3 {{
      margin: 0;
      font-size: 17px;
    }}

    .day-title a {{
      color: var(--blue);
      font-size: 13px;
      text-decoration: none;
      font-weight: 700;
    }}

    /* ── Section groups within a day ─────────────────────────────────────────── */
    .section-group {{
      margin-bottom: 18px;
    }}

    .section-group-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      border-radius: 10px;
      margin-bottom: 12px;
      font-size: 13px;
      font-weight: 700;
    }}

    .section-group-header[data-section="deep_learning_quant"] {{
      background: var(--blue-soft);
      color: #174ea6;
    }}

    .section-group-header[data-section="ai_quant_tools"] {{
      background: var(--green-soft);
      color: #137333;
    }}

    .section-group-header[data-section="daily_news"] {{
      background: var(--yellow-soft);
      color: #7a4f00;
    }}

    .sg-icon {{
      font-size: 15px;
      flex-shrink: 0;
    }}

    .sg-label {{
      flex: 1;
    }}

    .sg-count {{
      font-variant-numeric: tabular-nums;
      font-weight: 400;
      opacity: 0.75;
      font-size: 12px;
    }}

    /* ── Cards ───────────────────────────────────────────────────────────────── */
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 14px;
    }}

    .card {{
      position: relative;
      overflow: hidden;
      display: grid;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: 0 1px 2px rgba(60, 64, 67, 0.10);
      padding: 18px;
      transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
    }}

    .card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 4px;
      background: linear-gradient(90deg, var(--blue), var(--red), var(--yellow), var(--green));
    }}

    .card[data-section="deep_learning_quant"]::before {{
      background: linear-gradient(90deg, #1a73e8, #4285f4, #34a8f4);
    }}

    .card[data-section="ai_quant_tools"]::before {{
      background: linear-gradient(90deg, #34a853, #00c667, #34a853);
    }}

    .card[data-section="daily_news"]::before {{
      background: linear-gradient(90deg, #fbbc04, #f9a825, #ff9800);
    }}

    .card:hover {{
      border-color: #c6dafc;
      box-shadow: var(--shadow);
      transform: translateY(-2px);
    }}

    .card-top {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
    }}

    .card h4 {{
      margin: 0;
      font-size: 19px;
      line-height: 1.3;
    }}

    .score {{
      min-width: 52px;
      border-radius: 999px;
      background: var(--blue-soft);
      color: #174ea6;
      padding: 6px 8px;
      text-align: center;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}

    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }}

    .tag {{
      border: 1px solid transparent;
      border-radius: 999px;
      background: #f1f3f4;
      color: var(--muted);
      padding: 3px 8px;
      font-size: 12px;
    }}

    .tag:nth-child(1) {{ background: var(--blue-soft); color: #174ea6; }}
    .tag:nth-child(2) {{ background: var(--green-soft); color: #137333; }}
    .tag:nth-child(3) {{ background: var(--yellow-soft); color: #8a5a00; }}
    .tag:nth-child(4) {{ background: var(--red-soft); color: #b3261e; }}

    .summary {{
      margin: 0;
      color: #30342d;
      font-size: 14px;
      line-height: 1.48;
    }}

    .reader-format {{
      display: grid;
      gap: 8px;
    }}

    .reader-block {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}

    .reader-block:first-child {{
      border-top: 0;
      padding-top: 0;
    }}

    .reader-block h5 {{
      margin: 0 0 5px;
      color: var(--blue);
      font-size: 12px;
      font-weight: 700;
    }}

    .reader-block p,
    .reader-block li {{
      margin: 0;
      color: #30342d;
      font-size: 13px;
      line-height: 1.48;
    }}

    .reader-block:first-child p {{
      font-size: 15px;
      line-height: 1.52;
    }}

    .reader-block ol {{
      margin: 0;
      padding-left: 18px;
    }}

    .reader-reference {{
      color: var(--blue);
      text-decoration: none;
      font-weight: 800;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}

    .reference-url {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}

    .ref-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}

    .ref-row a {{
      color: var(--green);
      text-decoration: none;
      font-weight: 800;
      font-size: 13px;
    }}

    .ref-row small {{
      overflow: hidden;
      color: var(--muted);
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .empty {{
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.72);
      color: var(--muted);
      padding: 28px;
    }}

    /* ── Hero section ────────────────────────────────────────────────────────── */
    .hero-section {{
      margin-bottom: 22px;
    }}

    .hero-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px;
      font-size: 12px;
      font-weight: 800;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .hero-label::before {{
      content: "";
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--blue);
      animation: pulse 1.8s ease-in-out infinite;
      flex-shrink: 0;
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.45; transform: scale(0.8); }}
    }}

    .hero-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 14px;
    }}

    .hero-card {{
      position: relative;
      overflow: hidden;
      display: grid;
      gap: 12px;
      border: 1.5px solid #c6dafc;
      border-radius: 18px;
      background: linear-gradient(135deg, #f0f4ff 0%, #fff 60%);
      box-shadow: 0 2px 10px rgba(26, 115, 232, 0.13);
      padding: 20px;
      transition: transform 140ms ease, box-shadow 140ms ease;
    }}

    .hero-card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 4px;
      background: linear-gradient(90deg, var(--blue), var(--red), var(--yellow), var(--green));
    }}

    .hero-card:hover {{
      box-shadow: 0 6px 24px rgba(26, 115, 232, 0.22);
      transform: translateY(-3px);
    }}

    .hero-rank {{
      position: absolute;
      top: 14px;
      right: 14px;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: var(--blue);
      color: #fff;
      font-size: 11px;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .hero-card h4 {{
      margin: 0;
      font-size: 17px;
      line-height: 1.3;
      padding-right: 32px;
    }}

    /* ── Action buttons ──────────────────────────────────────────────────────── */
    .card-actions {{
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
    }}

    .action-btn {{
      height: 28px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: transparent;
      color: var(--muted);
      font-size: 12px;
      padding: 0 10px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 120ms;
      white-space: nowrap;
    }}

    .action-btn:hover {{
      border-color: var(--blue);
      color: var(--blue);
      background: var(--blue-soft);
    }}

    .action-btn.bookmarked {{
      border-color: #e6a800;
      color: #7a4f00;
      background: var(--yellow-soft);
    }}

    .card.read-done > .card-top > h4,
    .card.read-done > .card-top {{
      opacity: 0.55;
    }}

    mark {{
      background: #fff0a0;
      color: inherit;
      border-radius: 2px;
      padding: 0 1px;
    }}

    /* ── Crypto Alpha ─────────────────────────────────────────────────────────── */
    .alpha-banner {{
      position: relative;
      overflow: hidden;
      border: 1.5px solid #d2a8ff;
      border-radius: 20px;
      background: linear-gradient(135deg, #1a0533 0%, #0d1b2a 100%);
      padding: 22px 24px;
      margin-bottom: 28px;
      color: #e8d5ff;
    }}

    .alpha-banner::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 3px;
      background: linear-gradient(90deg, #a855f7, #ec4899, #f59e0b, #10b981);
    }}

    .alpha-banner-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }}

    .alpha-banner-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid #a855f7;
      border-radius: 999px;
      background: rgba(168, 85, 247, 0.18);
      color: #d8b4fe;
      font-size: 11px;
      font-weight: 800;
      padding: 4px 10px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}

    .alpha-conf-badge {{
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 10px;
    }}
    .alpha-conf-badge.high {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; }}
    .alpha-conf-badge.medium {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid #f59e0b; }}
    .alpha-conf-badge.low {{ background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid #6b7280; }}

    .alpha-name {{
      margin: 0 0 4px;
      font-size: 20px;
      font-weight: 800;
      color: #f3e8ff;
    }}

    .alpha-hypothesis {{
      margin: 0 0 16px;
      font-size: 14px;
      color: #c4b5fd;
      line-height: 1.5;
    }}

    .alpha-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .alpha-block {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 12px;
    }}

    .alpha-block-label {{
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #a78bfa;
      margin-bottom: 5px;
    }}

    .alpha-block-value {{
      font-size: 12px;
      color: #e2d9f3;
      line-height: 1.5;
    }}

    .alpha-sources {{
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      padding-top: 12px;
      margin-top: 4px;
    }}

    .alpha-sources-label {{
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #a78bfa;
      margin-bottom: 8px;
    }}

    .alpha-source-item {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 12px;
    }}

    .alpha-source-item a {{
      color: #818cf8;
      text-decoration: none;
      font-weight: 600;
    }}

    .alpha-source-item a:hover {{
      text-decoration: underline;
    }}

    .alpha-source-why {{
      color: #9ca3af;
      font-size: 11px;
    }}

    .alpha-quickstart {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 10px;
      padding: 10px 14px;
      margin-top: 12px;
      font-size: 12px;
      color: #6ee7b7;
    }}

    .alpha-quickstart strong {{
      display: block;
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #34d399;
      margin-bottom: 4px;
    }}

    .alpha-risks {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}

    .alpha-risk-tag {{
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 999px;
      color: #fca5a5;
      font-size: 11px;
      padding: 2px 9px;
    }}

    .alpha-hist-item {{
      border: 1px solid rgba(168, 85, 247, 0.25);
      border-radius: 10px;
      background: rgba(168, 85, 247, 0.05);
      padding: 8px 10px;
      margin-bottom: 7px;
      cursor: pointer;
      transition: background 120ms;
    }}

    .alpha-hist-item:hover {{
      background: rgba(168, 85, 247, 0.12);
    }}

    .alpha-hist-date {{
      font-size: 10px;
      color: #9ca3af;
      margin-bottom: 3px;
    }}

    .alpha-hist-name {{
      font-size: 12px;
      font-weight: 700;
      color: #c4b5fd;
      line-height: 1.3;
    }}

    /* ── Notes tab ───────────────────────────────────────────────────────────── */
    .notes-layout {{
      display: grid;
      grid-template-columns: 240px 1fr;
      height: calc(100vh - var(--topbar-h));
      overflow: hidden;
    }}

    .notes-sidebar {{
      border-right: 1px solid var(--line);
      overflow-y: auto;
      padding: 20px 14px;
    }}

    .note-nav-item {{
      border-radius: 10px;
      padding: 10px 12px;
      cursor: pointer;
      margin-bottom: 6px;
      transition: background 120ms;
    }}

    .note-nav-item:hover {{
      background: #f1f3f4;
    }}

    .note-nav-item.active {{
      background: var(--blue-soft);
      color: #174ea6;
    }}

    .note-nav-date {{
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 2px;
    }}

    .note-nav-item.active .note-nav-date {{
      color: #4285f4;
    }}

    .note-nav-title {{
      font-size: 13px;
      font-weight: 600;
      line-height: 1.35;
    }}

    .note-content {{
      overflow-y: auto;
      padding: 32px 48px;
    }}

    .note-header {{
      margin-bottom: 28px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}

    .note-date-label {{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      font-weight: 600;
      letter-spacing: 0.04em;
    }}

    .note-title {{
      margin: 0;
      font-size: 26px;
      font-weight: 700;
      line-height: 1.25;
      letter-spacing: -0.02em;
    }}

    /* ── Weekly tab ──────────────────────────────────────────────────────────── */
    .weekly-layout {{
      display: grid;
      grid-template-columns: 220px 1fr;
      height: calc(100vh - var(--topbar-h));
      overflow: hidden;
    }}

    .weekly-sidebar {{
      border-right: 1px solid var(--line);
      overflow-y: auto;
      padding: 20px 14px;
    }}

    .weekly-nav-item {{
      border-radius: 10px;
      padding: 10px 12px;
      cursor: pointer;
      margin-bottom: 8px;
      transition: background 120ms;
    }}

    .weekly-nav-item:hover {{
      background: #f1f3f4;
    }}

    .weekly-nav-item.active {{
      background: var(--blue-soft);
      color: #174ea6;
    }}

    .weekly-nav-week {{
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 2px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .weekly-nav-item.active .weekly-nav-week {{
      color: #4285f4;
    }}

    .weekly-nav-title {{
      font-size: 13px;
      font-weight: 700;
      line-height: 1.3;
      margin-bottom: 3px;
    }}

    .weekly-nav-subtitle {{
      font-size: 11px;
      color: var(--muted);
      line-height: 1.4;
    }}

    .weekly-nav-item.active .weekly-nav-subtitle {{
      color: #4285f4;
    }}

    .weekly-content {{
      overflow-y: auto;
      padding: 32px 48px;
    }}

    .weekly-subtitle {{
      margin: 8px 0 0;
      font-size: 15px;
      color: var(--muted);
      font-style: italic;
    }}

    /* ── Markdown rendered content ───────────────────────────────────────────── */
    .md-content {{
      max-width: 820px;
      line-height: 1.7;
      color: var(--ink);
      font-size: 15px;
    }}

    .md-content h1 {{
      font-size: 24px;
      margin: 32px 0 16px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }}

    .md-content h1:first-child {{
      margin-top: 0;
    }}

    .md-content h2 {{
      font-size: 20px;
      margin: 28px 0 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--line);
    }}

    .md-content h3 {{
      font-size: 17px;
      margin: 22px 0 10px;
    }}

    .md-content h4, .md-content h5, .md-content h6 {{
      font-size: 15px;
      margin: 18px 0 8px;
    }}

    .md-content p {{
      margin: 12px 0;
    }}

    .md-content ul, .md-content ol {{
      margin: 10px 0;
      padding-left: 24px;
    }}

    .md-content li {{
      margin-bottom: 5px;
    }}

    .md-content code {{
      background: #f1f3f4;
      border: 1px solid var(--line);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
      font-family: "Courier New", "Consolas", monospace;
    }}

    .md-content pre {{
      background: #f8f9fa;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 16px 18px;
      overflow-x: auto;
      margin: 14px 0;
    }}

    .md-content pre code {{
      background: none;
      border: none;
      padding: 0;
      font-size: 13px;
    }}

    .md-content blockquote {{
      border-left: 3px solid var(--blue);
      margin: 16px 0;
      padding: 10px 18px;
      background: var(--blue-soft);
      border-radius: 0 8px 8px 0;
      color: #174ea6;
    }}

    .md-content blockquote p {{
      margin: 0;
    }}

    .md-content table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
      font-size: 14px;
    }}

    .md-content th, .md-content td {{
      border: 1px solid var(--line);
      padding: 8px 14px;
      text-align: left;
    }}

    .md-content th {{
      background: #f1f3f4;
      font-weight: 700;
    }}

    .md-content tr:nth-child(even) td {{
      background: #fafafa;
    }}

    .md-content img {{
      max-width: 100%;
      border-radius: 8px;
      margin: 8px 0;
    }}

    .md-content a {{
      color: var(--blue);
    }}

    .md-content hr {{
      border: none;
      border-top: 1px solid var(--line);
      margin: 24px 0;
    }}

    /* ── Onboarding overlay ──────────────────────────────────────────────────── */
    .ob-overlay {{
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(32, 33, 36, 0.55);
      backdrop-filter: blur(6px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}

    .ob-overlay.hidden {{
      display: none;
    }}

    .ob-modal {{
      width: 100%;
      max-width: 680px;
      border-radius: 24px;
      background: #fff;
      box-shadow: 0 8px 48px rgba(32, 33, 36, 0.28);
      padding: 36px;
      animation: ob-in 220ms ease;
    }}

    @keyframes ob-in {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}

    .ob-header {{
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 24px;
    }}

    .ob-logo {{
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: conic-gradient(from 0deg, var(--blue) 0 25%, var(--red) 0 50%, var(--yellow) 0 75%, var(--green) 0 100%);
      box-shadow: inset 0 0 0 10px #fff;
      flex-shrink: 0;
    }}

    .ob-header h2 {{
      margin: 0;
      font-size: 20px;
      font-weight: 700;
    }}

    .ob-header p {{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .ob-steps {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-bottom: 28px;
    }}

    .ob-step {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
    }}

    .ob-step-icon {{
      font-size: 24px;
      line-height: 1;
      margin-bottom: 10px;
    }}

    .ob-step h3 {{
      margin: 0 0 6px;
      font-size: 13px;
      font-weight: 700;
      color: var(--blue);
    }}

    .ob-step p {{
      margin: 0;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.55;
    }}

    .ob-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}

    .ob-footer small {{
      color: var(--muted);
      font-size: 12px;
    }}

    .ob-btn {{
      height: 42px;
      border: none;
      border-radius: 999px;
      background: var(--blue);
      color: #fff;
      font-size: 14px;
      font-weight: 700;
      padding: 0 24px;
      cursor: pointer;
      transition: background 140ms;
    }}

    .ob-btn:hover {{
      background: #1557b0;
    }}

    .help-btn {{
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
      padding: 0 14px;
      cursor: pointer;
      white-space: nowrap;
    }}

    .help-btn:hover {{
      border-color: var(--blue);
      color: var(--blue);
    }}

    .nav-hint {{
      font-size: 11px;
      color: var(--blue);
      margin: 4px 0 10px 10px;
      opacity: 0.8;
    }}

    @media (max-width: 1100px) {{
      .layout {{
        grid-template-columns: 240px 1fr;
      }}
    }}

    @media (max-width: 860px) {{
      .topbar-main {{
        grid-template-columns: 1fr auto;
      }}

      .controls {{
        display: none;
      }}

      .layout {{
        grid-template-columns: 1fr;
      }}

      .rail {{
        position: static;
        height: auto;
      }}

      .notes-layout, .weekly-layout {{
        grid-template-columns: 1fr;
        height: auto;
      }}

      .notes-sidebar, .weekly-sidebar {{
        border-right: none;
        border-bottom: 1px solid var(--line);
        max-height: 220px;
        overflow-y: auto;
      }}

      .note-content, .weekly-content {{
        padding: 20px 16px;
      }}
    }}

    @media (max-width: 620px) {{
      .topbar-main,
      .layout {{
        padding: 12px;
      }}

      .tab-row {{
        padding: 0 12px;
      }}

      .tab-btn {{
        padding: 0 12px;
        font-size: 13px;
      }}

      .metric-grid,
      .cards,
      .hero-grid {{
        grid-template-columns: 1fr;
      }}

      .ob-steps {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <!-- First-visit onboarding overlay -->
  <div class="ob-overlay hidden" id="ob-overlay">
    <div class="ob-modal">
      <div class="ob-header">
        <div class="ob-logo"></div>
        <div>
          <h2>欢迎使用 samson 量化情报台</h2>
          <p>每天自动聚合 arXiv 论文、量化论坛、知乎和 QuantML，生成结构化中文情报</p>
        </div>
      </div>
      <div class="ob-steps">
        <div class="ob-step">
          <div class="ob-step-icon">&#128250;</div>
          <h3>三大分区</h3>
          <p>
            <b>今日情报</b>——按分区看当天重点资讯<br>
            <b>我的随笔</b>——记录正在做的研究思考<br>
            <b>周报</b>——完整周报供老板随时查阅
          </p>
        </div>
        <div class="ob-step">
          <div class="ob-step-icon">&#128196;</div>
          <h3>四段式阅读格式</h3>
          <p>每条情报统一展示：<br>
            1. 太长不读<br>
            2. 对量化工作的价值<br>
            3. 关键核心点<br>
            4. 原文链接
          </p>
        </div>
        <div class="ob-step">
          <div class="ob-step-icon">&#128269;</div>
          <h3>搜索和过滤</h3>
          <p>顶栏可按关键词搜索全文，左侧可按日期、主线、细分标签组合筛选。<br>点「打开当日看板」进入详情视图。</p>
        </div>
      </div>
      <div class="ob-footer">
        <small>下次不再显示 · 右上角「使用指南」可随时重新打开</small>
        <button class="ob-btn" id="ob-dismiss">了解了，开始使用</button>
      </div>
    </div>
  </div>

  <header class="topbar">
    <div class="topbar-main">
      <div class="brand">
        <h1>samson 量化情报台</h1>
        <p id="range-label"></p>
      </div>
      <div class="controls" id="intel-controls">
        <input class="control" id="search" type="search" placeholder="搜索标题、摘要、来源..." />
        <select class="control" id="day-select"></select>
        <select class="control" id="section-select"></select>
        <select class="control" id="category-select"></select>
      </div>
      <button class="help-btn" id="help-btn">使用指南</button>
    </div>
    <nav class="tab-row">
      <button class="tab-btn active" data-tab="intel">&#128225; 今日情报</button>
      <button class="tab-btn" data-tab="notes">&#9997; 我的随笔</button>
      <button class="tab-btn" data-tab="weekly">&#128203; 周报</button>
    </nav>
  </header>

  <!-- Tab panel: 今日情报 -->
  <div class="tab-panel" id="panel-intel">
    <main class="layout">
      <aside class="rail">
        <div class="metric-grid">
          <div class="metric"><b id="metric-items">0</b><span>总资讯</span></div>
          <div class="metric"><b id="metric-days">0</b><span>覆盖天数</span></div>
          <div class="metric"><b id="metric-high">0</b><span>高优先级</span></div>
          <div class="metric"><b id="metric-refs">0</b><span>原文链接</span></div>
        </div>

        <div class="section-label">日期</div>
        <div class="nav-list" id="day-list"></div>

        <div class="section-label">两条主线 <span style="font-weight:400;color:var(--muted)">· 点击筛选</span></div>
        <div class="nav-hint" id="section-hint">&#x1F449; 选择方向，快速定位今日重点</div>
        <div class="nav-list" id="section-list"></div>

        <div class="section-label">细分标签</div>
        <div class="nav-list" id="category-list"></div>

        <div class="section-label">&#9889; Crypto Alpha 历史</div>
        <div id="alpha-hist-list"></div>

        <div class="section-label">我的收藏</div>
        <div class="nav-list">
          <button class="nav-button" type="button" id="bookmarks-btn">
            <span>&#128278; 收藏夹</span>
            <span class="count" id="bookmark-count">0</span>
          </button>
        </div>

        <div class="section-label">主力来源</div>
        <ul class="source-list" id="source-list"></ul>
      </aside>

      <section>
        <div class="feed-head">
          <h2 id="feed-title">最近资讯</h2>
          <span id="result-count"></span>
        </div>
        <div id="alpha-container"></div>
        <div id="feed"></div>
      </section>
    </main>
  </div>

  <!-- Tab panel: 我的随笔 -->
  <div class="tab-panel hidden" id="panel-notes">
    <div class="notes-layout">
      <aside class="notes-sidebar">
        <div class="section-label" style="margin-top:8px">随笔列表</div>
        <div id="notes-nav"></div>
      </aside>
      <article id="note-content" class="note-content"></article>
    </div>
  </div>

  <!-- Tab panel: 周报 -->
  <div class="tab-panel hidden" id="panel-weekly">
    <div class="weekly-layout">
      <aside class="weekly-sidebar">
        <div class="section-label" style="margin-top:8px">研究周报</div>
        <div id="weekly-nav"></div>
      </aside>
      <article id="weekly-content" class="weekly-content"></article>
    </div>
  </div>

  <script>
    // ── API-driven dashboard — no embedded data ───────────────────────────────
    const state = {{ date: 'All', section: 'All', category: 'All', q: '', offset: 0, loading: false, bookmarksOnly: false }};
    const LIMIT = 30;
    let summaryData = {{}};
    let categoryLabels = {{}};
    let priorityLabels = {{}};
    let sourceTypeLabels = {{}};
    let currentItems = [];
    let totalCount = 0;
    let alphaHistory = [];
    let activeAlphaIdx = 0;
    const notesData = [];
    const weeklyData = [];
    const $ = function(id) {{ return document.getElementById(id); }};

    // Section definitions for grouped feed view
    const SECTION_DEFS = [
      {{ key: 'deep_learning_quant', label: '深度学习量化未来', icon: '&#129504;' }},
      {{ key: 'ai_quant_tools', label: 'AI 量化工具', icon: '&#128736;' }},
      {{ key: 'daily_news', label: '量化每日新闻', icon: '&#128240;' }},
    ];

    // ── Tab switching ─────────────────────────────────────────────────────────
    function switchTab(tab) {{
      document.querySelectorAll('.tab-btn').forEach(function(btn) {{
        btn.classList.toggle('active', btn.dataset.tab === tab);
      }});
      document.querySelectorAll('.tab-panel').forEach(function(panel) {{
        panel.classList.toggle('hidden', panel.id !== 'panel-' + tab);
      }});
      const controls = $('intel-controls');
      if (controls) controls.style.visibility = tab === 'intel' ? 'visible' : 'hidden';
      if (history.replaceState) {{
        history.replaceState(null, '', tab === 'intel' ? location.pathname : '#' + tab);
      }}
    }}

    document.querySelectorAll('.tab-btn').forEach(function(btn) {{
      btn.addEventListener('click', function() {{ switchTab(btn.dataset.tab); }});
    }});

    // ── Notes tab ─────────────────────────────────────────────────────────────
    function buildNotesNav() {{
      const nav = $('notes-nav');
      if (!notesData.length) {{
        nav.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:8px 4px;line-height:1.6">暂无随笔。<br>在 <code>notes/YYYY-MM-DD.md</code> 创建第一篇。</p>';
        const content = $('note-content');
        if (content) content.innerHTML = '<div style="text-align:center;color:var(--muted);padding:80px 20px;font-size:15px">暂无随笔</div>';
        return;
      }}
      nav.innerHTML = notesData.map(function(note, i) {{
        return '<div class="note-nav-item' + (i === 0 ? ' active' : '') + '" onclick="showNote(' + i + ')">' +
          '<div class="note-nav-date">' + escapeHtml(note.date) + '</div>' +
          '<div class="note-nav-title">' + escapeHtml(note.title || note.date) + '</div>' +
          '</div>';
      }}).join('');
      showNote(0);
    }}

    function showNote(idx) {{
      document.querySelectorAll('.note-nav-item').forEach(function(el, i) {{
        el.classList.toggle('active', i === idx);
      }});
      const note = notesData[idx];
      if (!note) return;
      $('note-content').innerHTML =
        '<div class="note-header">' +
          '<div class="note-date-label">' + escapeHtml(note.date) + '</div>' +
          '<h1 class="note-title">' + escapeHtml(note.title || note.date) + '</h1>' +
        '</div>' +
        '<div class="md-content">' + (note.body_html || '<p style="color:var(--muted)">（无内容）</p>') + '</div>';
    }}

    // ── Weekly tab ────────────────────────────────────────────────────────────
    var _sortedWeekly = weeklyData.slice().sort(function(a, b) {{ return b.week - a.week; }});

    function buildWeeklyNav() {{
      const nav = $('weekly-nav');
      if (!_sortedWeekly.length) {{
        nav.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:8px 4px;line-height:1.6">暂无周报。<br>在 <code>weekly_report/week*.md</code> 新建。</p>';
        const content = $('weekly-content');
        if (content) content.innerHTML = '<div style="text-align:center;color:var(--muted);padding:80px 20px;font-size:15px">暂无周报</div>';
        return;
      }}
      nav.innerHTML = _sortedWeekly.map(function(report, i) {{
        return '<div class="weekly-nav-item' + (i === 0 ? ' active' : '') + '" onclick="showWeekly(' + i + ')">' +
          '<div class="weekly-nav-week">WEEK ' + escapeHtml(String(report.week)) + '</div>' +
          '<div class="weekly-nav-title">' + escapeHtml(report.title || report.id || '') + '</div>' +
          (report.subtitle ? '<div class="weekly-nav-subtitle">' + escapeHtml(report.subtitle) + '</div>' : '') +
          '</div>';
      }}).join('');
      showWeekly(0);
    }}

    function showWeekly(idx) {{
      document.querySelectorAll('.weekly-nav-item').forEach(function(el, i) {{
        el.classList.toggle('active', i === idx);
      }});
      const report = _sortedWeekly[idx];
      if (!report) return;
      $('weekly-content').innerHTML =
        '<div class="note-header">' +
          '<div class="note-date-label">WEEK ' + escapeHtml(String(report.week)) + ' &nbsp;·&nbsp; ' + escapeHtml(report.filename || '') + '</div>' +
          '<h1 class="note-title">' + escapeHtml(report.title || report.id || '') + '</h1>' +
          (report.subtitle ? '<p class="weekly-subtitle">' + escapeHtml(report.subtitle) + '</p>' : '') +
        '</div>' +
        '<div class="md-content">' + (report.html || '<p style="color:var(--muted)">（无内容）</p>') + '</div>';
    }}

    // ── API helpers (live API → static JSON fallback for GitHub Pages) ───────────
    let _staticItemsCache = null;

    async function apiGet(url) {{
      // Try live API first (works when serve.py is running)
      try {{
        const r = await fetch(url);
        if (r.ok) return r.json();
      }} catch(e) {{}}

      // Static fallback — pre-generated JSON files for GitHub Pages
      const path = url.split('?')[0].replace(/.*\/(api\/)/, '$1');
      const params = new URLSearchParams(url.includes('?') ? url.split('?')[1] : '');

      if (path === 'api/summary') {{
        const r = await fetch('api/summary.json');
        if (r.ok) return r.json();
      }}
      if (path === 'api/items') {{
        if (!_staticItemsCache) {{
          const r = await fetch('api/items.json');
          if (!r.ok) throw new Error('Static items.json not found');
          const d = await r.json();
          _staticItemsCache = d.items || [];
        }}
        return _filterStatic(_staticItemsCache, params);
      }}
      if (path === 'api/alpha') {{
        try {{ const r = await fetch('api/alpha.json'); if (r.ok) return r.json(); }} catch(e) {{}}
        return {{ history: [] }};
      }}
      throw new Error('API unavailable: ' + url);
    }}

    function _filterStatic(all, params) {{
      let items = all.slice();
      const reqDate = params.get('date') || '';
      const section = params.get('section') || 'All';
      const category = params.get('category') || 'All';
      const q = (params.get('q') || '').toLowerCase().trim();
      if (reqDate) items = items.filter(function(i) {{ return String(i.collected_at || '').startsWith(reqDate); }});
      if (section !== 'All') items = items.filter(function(i) {{ return (i.report_sections || []).includes(section); }});
      if (category !== 'All') items = items.filter(function(i) {{ return i.category === category; }});
      if (q) items = items.filter(function(i) {{
        const t = [i.title, i.display_title, i.one_line_summary, i.tldr, i.core_value, i.source, i.category, i.source_type].join(' ').toLowerCase();
        return t.includes(q);
      }});
      const total = items.length;
      const offset = parseInt(params.get('offset') || '0');
      const limit = parseInt(params.get('limit') || '30');
      return {{ items: items.slice(offset, offset + limit), total: total, offset: offset, limit: limit }};
    }}

    // ── Boot (async, API-driven) ───────────────────────────────────────────────
    async function boot() {{
      try {{
        summaryData = await apiGet('/api/summary');
        categoryLabels = summaryData.category_labels || {{}};
        priorityLabels = summaryData.priority_labels || {{}};
        sourceTypeLabels = summaryData.source_type_labels || {{}};

        const days = summaryData.days || [];
        if (days.length > 0) state.date = days[0].date;

        $('range-label').textContent = '主力源：arXiv / QuantML / Crypto News · 最近 ' + summaryData.history_days + ' 天 · 截止 ' + summaryData.end_date;
        $('metric-days').textContent = days.length;

        buildDayControls();
        buildSectionControls();
        buildCategoryControls();
        buildSourceList();
        bindControls();
        updateBookmarkCount();
        buildNotesNav();
        buildWeeklyNav();

        const alphaData = await apiGet('/api/alpha');
        alphaHistory = alphaData.history || [];
        buildAlphaHistoryNav();
        renderAlphaBanner();

        await loadItems(true);
      }} catch(e) {{
        console.error('Boot failed:', e);
        $('feed').innerHTML = '<div class="empty">加载失败，请确认 serve.py 正在运行。<br><small>' + escapeHtml(String(e)) + '</small></div>';
      }}
    }}

    async function loadItems(reset) {{
      if (state.loading) return;
      state.loading = true;
      if (reset) {{ state.offset = 0; currentItems = []; }}

      const params = new URLSearchParams();
      if (state.date !== 'All') params.set('date', state.date);
      if (state.section !== 'All') params.set('section', state.section);
      if (state.category !== 'All') params.set('category', state.category);
      if (state.q) params.set('q', state.q);
      params.set('offset', state.offset);
      params.set('limit', LIMIT);

      try {{
        const data = await apiGet('/api/items?' + params);
        currentItems = reset ? data.items : currentItems.concat(data.items);
        totalCount = data.total;
        state.offset = currentItems.length;
        renderFeed();
        $('metric-items').textContent = totalCount;
        $('metric-high').textContent = currentItems.filter(function(i) {{ return priorityLabel(i.read_priority) === '高'; }}).length;
        $('result-count').textContent = '展示 ' + currentItems.length + ' / ' + totalCount + ' 条';
        $('feed-title').textContent = feedTitle();
        markActive();
      }} finally {{
        state.loading = false;
      }}
    }}

    function bindControls() {{
      var searchTimer;
      $('search').addEventListener('input', function(e) {{
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {{
          state.q = e.target.value.trim().toLowerCase();
          loadItems(true);
        }}, 300);
      }});
      $('bookmarks-btn').addEventListener('click', function() {{
        state.bookmarksOnly = !state.bookmarksOnly;
        $('bookmarks-btn').classList.toggle('active', state.bookmarksOnly);
        renderFeed();
      }});
      $('day-select').addEventListener('change', function(e) {{
        state.date = e.target.value;
        loadItems(true);
      }});
      $('section-select').addEventListener('change', function(e) {{
        state.section = e.target.value;
        loadItems(true);
      }});
      $('category-select').addEventListener('change', function(e) {{
        state.category = e.target.value;
        loadItems(true);
      }});
    }}

    function buildDayControls() {{
      const days = summaryData.days || [];
      const total = days.reduce(function(s, d) {{ return s + d.count; }}, 0);
      $('day-select').innerHTML = option('All', '全部日期 (' + total + ')') +
        days.map(function(d, i) {{ return option(d.date, (i === 0 ? '今日 ' : '') + d.date + ' (' + d.count + ')'); }}).join('');
      $('day-list').innerHTML = navButton('date', 'All', '全部', total) +
        days.map(function(d, i) {{ return navButton('date', d.date, i === 0 ? '今日 ' + d.date : d.date, d.count); }}).join('');
      $('day-select').value = state.date;
      bindNav('date');
    }}

    function buildSectionControls() {{
      const sections = summaryData.sections || [];
      $('section-select').innerHTML = option('All', '全部主线') +
        sections.map(function(s) {{ return option(s.key, s.label); }}).join('');
      $('section-list').innerHTML = navButton('section', 'All', '全部', '') +
        sections.map(function(s) {{ return navButton('section', s.key, s.label, ''); }}).join('');
      bindNav('section');
    }}

    function buildCategoryControls() {{
      const counts = summaryData.category_counts || {{}};
      const categories = Object.keys(counts).sort();
      $('category-select').innerHTML = option('All', '全部细分标签') +
        categories.map(function(c) {{ return option(c, categoryLabel(c) + ' (' + counts[c] + ')'); }}).join('');
      $('category-list').innerHTML = navButton('category', 'All', '全部', '') +
        categories.map(function(c) {{ return navButton('category', c, categoryLabel(c), counts[c]); }}).join('');
      bindNav('category');
    }}

    function buildSourceList() {{
      const entries = Object.entries(summaryData.source_stats || {{}}).sort(function(a, b) {{ return b[1] - a[1]; }});
      $('source-list').innerHTML = entries.length
        ? entries.map(function(e) {{ return '<li><span>' + escapeHtml(e[0]) + '</span><b>' + e[1] + '</b></li>'; }}).join('')
        : '<li><span>暂无来源</span><b>0</b></li>';
    }}

    function bindNav(kind) {{
      document.querySelectorAll('[data-kind="' + kind + '"]').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
          const value = btn.dataset.value;
          state[kind] = value;
          const sel = $(kind === 'date' ? 'day-select' : kind + '-select');
          if (sel) sel.value = value;
          if (value === 'All' && (kind === 'section' || kind === 'category')) {{
            state.section = 'All'; state.category = 'All';
            $('section-select').value = 'All'; $('category-select').value = 'All';
          }}
          loadItems(true);
        }});
      }});
    }}

    // ── Render feed (uses currentItems, server-side filtered) ─────────────────
    function renderFeed() {{
      const feed = $('feed');
      let visible = currentItems;
      if (state.bookmarksOnly) {{
        visible = visible.filter(function(item) {{ return isBookmarked(item.id || item.url); }});
      }}
      if (!visible.length) {{
        feed.innerHTML = '<div class="empty">' + (state.loading ? '加载中...' : '当前筛选条件下没有资讯。') + '</div>';
        return;
      }}
      const grouped = groupByDay(visible);
      const sortedDays = Object.keys(grouped).sort().reverse();
      const mostRecentDay = sortedDays[0];
      const isSectionFiltered = state.section !== 'All';

      feed.innerHTML = sortedDays.map(function(day, idx) {{
        const dayItems = grouped[day];
        const heroHtml = idx === 0 && !state.bookmarksOnly ? renderHero(dayItems) : '';
        var sectionedHtml;
        if (isSectionFiltered) {{
          sectionedHtml = '<div class="cards">' + dayItems.map(card).join('') + '</div>';
        }} else {{
          sectionedHtml = SECTION_DEFS.map(function(s) {{
            const sItems = dayItems.filter(function(item) {{
              return (item.report_sections || []).includes(s.key);
            }});
            if (!sItems.length) return '';
            return '<div class="section-group">' +
              '<div class="section-group-header" data-section="' + escapeAttr(s.key) + '">' +
              '<span class="sg-icon">' + s.icon + '</span>' +
              '<span class="sg-label">' + s.label + '</span>' +
              '<span class="sg-count">' + sItems.length + ' 篇</span>' +
              '</div>' +
              '<div class="cards">' + sItems.map(card).join('') + '</div>' +
              '</div>';
          }}).join('');
        }}
        const dayLabel = escapeHtml(day === mostRecentDay ? '今日 ' + day : day);
        return '<section class="day-group">' +
          '<div class="day-title"><h3>' + dayLabel + '</h3>' +
          '<a href="' + escapeAttr(day + '.html') + '">打开当日看板</a></div>' +
          heroHtml + sectionedHtml + '</section>';
      }}).join('') + (currentItems.length < totalCount
        ? '<div style="text-align:center;padding:24px">' +
          '<button class="ob-btn" onclick="loadItems(false)">加载更多（剩余 ' + (totalCount - currentItems.length) + ' 条）</button>' +
          '</div>' : '');
    }}

    function card(item) {{
      const itemId = item.id || item.url || item.title || '';
      const section = (item.report_sections || [])[0] || '';
      const bmed = isBookmarked(itemId);
      return '<article class="card" data-section="' + escapeAttr(section) + '">' +
        '<div class="card-top">' +
        '<h4>' + highlight(item.display_title || item.title, state.q) + '</h4>' +
        '<div class="score">' + Number(item.final_score || 0).toFixed(1) + '</div>' +
        '</div>' +
        '<div class="meta">' +
        '<span class="tag">' + escapeHtml((item.report_section_labels || [])[0] || '其他') + '</span>' +
        '<span class="tag">' + escapeHtml(categoryLabel(item.category)) + '</span>' +
        '<span class="tag">' + escapeHtml(sourceTypeLabel(item.source_type)) + '</span>' +
        '<span class="tag">' + escapeHtml(priorityLabel(item.read_priority)) + '</span>' +
        '</div>' +
        '<div class="card-actions">' +
        '<button class="action-btn ' + (bmed ? 'bookmarked' : '') + '" data-bmid="' + escapeAttr(itemId) + '"' +
        ' onclick="toggleBookmark(this.dataset.bmid)" title="' + (bmed ? '取消收藏' : '收藏') + '">' +
        (bmed ? '&#128278;' : '&#128276;') + ' <span class="bm-label">' + (bmed ? '已收藏' : '收藏') + '</span>' +
        '</button>' +
        '</div>' +
        readerFormat(item) +
        '</article>';
    }}

    function readerFormat(item) {{
      const points = itemKeyPoints(item);
      return '<div class="reader-format">' +
        '<div class="reader-block">' +
        '<h5>1. 这篇文章的太长不读</h5>' +
        '<p>' + highlight(item.tldr || item.one_line_summary || '', state.q) + '</p>' +
        '</div>' +
        '<div class="reader-block">' +
        '<h5>2. 核心价值，对我量化的工作能够提供什么样的帮助</h5>' +
        '<p>' + escapeHtml(item.core_value || '') + '</p>' +
        '</div>' +
        '<div class="reader-block">' +
        '<h5>3. 关键核心点 / 论文或帖子摘要</h5>' +
        '<ol>' + points.map(function(p) {{ return '<li>' + escapeHtml(p) + '</li>'; }}).join('') + '</ol>' +
        '</div>' +
        '<div class="reader-block">' +
        '<h5>4. 原文链接</h5>' +
        referenceHtml(item) +
        '</div>' +
        '</div>';
    }}

    function itemKeyPoints(item) {{
      const points = Array.isArray(item.key_points_list) ? item.key_points_list
        : (Array.isArray(item.key_points) ? item.key_points : []);
      const clean = points.filter(Boolean).slice(0, 3);
      return clean.length ? clean : ['需要打开原文进一步确认方法、数据和适用边界。'];
    }}

    function referenceHtml(item) {{
      const url = item.reference_url || '';
      if (!url) return '<p>暂无可打开链接</p>';
      return '<a class="reader-reference" href="' + escapeAttr(url) + '" target="_blank" rel="noopener noreferrer">打开原文</a>' +
        '<small class="reference-url">' + escapeHtml(url) + '</small>';
    }}

    function markActive() {{
      document.querySelectorAll('.nav-button[data-kind]').forEach(function(btn) {{
        btn.classList.toggle('active', state[btn.dataset.kind] === btn.dataset.value);
      }});
    }}

    function feedTitle() {{
      const days = (summaryData.days || []).map(function(d) {{ return d.date; }});
      const isToday = state.date !== 'All' && days.length > 0 && state.date === days[0];
      const parts = [];
      if (state.date !== 'All') parts.push(isToday ? '今日情报' : state.date);
      if (state.section !== 'All') parts.push(sectionLabel(state.section));
      if (state.category !== 'All') parts.push(categoryLabel(state.category));
      return parts.length ? parts.join(' / ') : '全部情报';
    }}

    function groupByDay(list) {{
      return list.reduce(function(acc, item) {{
        const day = dayOf(item);
        acc[day] = acc[day] || [];
        acc[day].push(item);
        return acc;
      }}, {{}});
    }}

    function dayOf(item) {{
      return String(item.collected_at || '').slice(0, 10) || 'unknown';
    }}

    function navButton(kind, value, label, count) {{
      return '<button class="nav-button" type="button" data-kind="' + escapeAttr(kind) + '" data-value="' + escapeAttr(value) + '">' +
        '<span>' + escapeHtml(label) + '</span>' +
        '<span class="count">' + count + '</span>' +
        '</button>';
    }}

    function option(value, label) {{
      return '<option value="' + escapeAttr(value) + '">' + escapeHtml(label) + '</option>';
    }}

    function categoryLabel(c) {{ return categoryLabels[c] || c; }}
    function priorityLabel(p) {{ return priorityLabels[p] || p; }}
    function sourceTypeLabel(st) {{ return sourceTypeLabels[st] || st; }}

    function sectionLabel(key) {{
      const s = (summaryData.sections || []).find(function(item) {{ return item.key === key; }});
      return s ? s.label : '其他';
    }}

    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }}

    function escapeAttr(value) {{
      return escapeHtml(value).replaceAll('`', '&#096;');
    }}

    function highlight(text, q) {{
      if (!q) return escapeHtml(text);
      const escaped = escapeHtml(text);
      const safe = q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
      return escaped.replace(new RegExp('(' + safe + ')', 'gi'), '<mark>$1</mark>');
    }}

    // ── Bookmarks ─────────────────────────────────────────────────────────────
    const BM_KEY = 'samson_quant_bookmarks_v1';
    function getBookmarks() {{
      try {{ return JSON.parse(localStorage.getItem(BM_KEY) || '[]'); }}
      catch {{ return []; }}
    }}
    function isBookmarked(id) {{ return getBookmarks().includes(id); }}
    function toggleBookmark(id) {{
      const bm = getBookmarks();
      const idx = bm.indexOf(id);
      if (idx >= 0) bm.splice(idx, 1); else bm.push(id);
      localStorage.setItem(BM_KEY, JSON.stringify(bm));
      updateBookmarkCount();
      markActive();
      if (state.bookmarksOnly) renderFeed();
      else document.querySelectorAll('[data-bmid="' + id + '"]').forEach(function(btn) {{
        btn.classList.toggle('bookmarked', isBookmarked(id));
        btn.title = isBookmarked(id) ? '取消收藏' : '收藏';
        btn.querySelector('.bm-label').textContent = isBookmarked(id) ? '已收藏' : '收藏';
      }});
    }}
    function updateBookmarkCount() {{
      $('bookmark-count').textContent = getBookmarks().length;
      $('bookmarks-btn').classList.toggle('active', state.bookmarksOnly);
    }}

    // ── Crypto Alpha ──────────────────────────────────────────────────────────
    function buildAlphaHistoryNav() {{
      const list = $('alpha-hist-list');
      if (!alphaHistory.length) {{
        list.innerHTML = '<div style="font-size:11px;color:var(--muted);padding:4px 0 10px 2px">暂无 Alpha 记录，运行完整 pipeline 后生成</div>';
        return;
      }}
      list.innerHTML = alphaHistory.map(function(a, i) {{
        return '<div class="alpha-hist-item ' + (i === 0 ? 'active' : '') + '" onclick="showAlpha(' + i + ')">' +
          '<div class="alpha-hist-date">' + (a.date || '') + '</div>' +
          '<div class="alpha-hist-name">' + escapeHtml(a.alpha_name || '未命名') + '</div>' +
          '</div>';
      }}).join('');
    }}

    function showAlpha(idx) {{
      activeAlphaIdx = idx;
      document.querySelectorAll('.alpha-hist-item').forEach(function(el, i) {{
        el.classList.toggle('active', i === idx);
      }});
      renderAlphaBanner();
    }}

    function renderAlphaBanner() {{
      const container = $('alpha-container');
      if (!container) return;
      if (!alphaHistory.length) {{ container.innerHTML = ''; return; }}
      const a = alphaHistory[activeAlphaIdx] || {{}};
      const conf = (a.confidence || 'medium').toLowerCase();
      const confLabels = {{ high: '高信心', medium: '中等信心', low: '低信心' }};
      const sources = Array.isArray(a.supporting_sources) ? a.supporting_sources : [];
      const risks = Array.isArray(a.risk_factors) ? a.risk_factors : [];
      const data = Array.isArray(a.data_needed) ? a.data_needed : [];
      container.innerHTML =
        '<div class="alpha-banner">' +
        '<div class="alpha-banner-header">' +
        '<span class="alpha-banner-badge">&#9889; Crypto Alpha &middot; ' + escapeHtml(a.date || '') + '</span>' +
        '<span class="alpha-conf-badge ' + conf + '">' + escapeHtml(confLabels[conf] || conf) + '</span>' +
        '</div>' +
        '<h3 class="alpha-name">' + escapeHtml(a.alpha_name || '未命名') + '</h3>' +
        '<p class="alpha-hypothesis">' + escapeHtml(a.hypothesis || '') + '</p>' +
        '<div class="alpha-grid">' +
        '<div class="alpha-block"><div class="alpha-block-label">&#128268; 信号逻辑</div><div class="alpha-block-value">' + escapeHtml(a.signal_logic || '') + '</div></div>' +
        '<div class="alpha-block"><div class="alpha-block-label">&#128202; 所需数据</div><div class="alpha-block-value">' + data.map(function(d) {{ return '&bull; ' + escapeHtml(d); }}).join('<br>') + '</div></div>' +
        '<div class="alpha-block"><div class="alpha-block-label">&#128200; 回测方案</div><div class="alpha-block-value">' + escapeHtml(a.backtest_approach || '') + '</div></div>' +
        '</div>' +
        (risks.length ? '<div class="alpha-risks">' + risks.map(function(r) {{ return '<span class="alpha-risk-tag">&#9888; ' + escapeHtml(r) + '</span>'; }}).join('') + '</div>' : '') +
        (a.quick_start ? '<div class="alpha-quickstart"><strong>&#128640; 今天的第一步</strong>' + escapeHtml(a.quick_start) + '</div>' : '') +
        (sources.length ?
          '<div class="alpha-sources"><div class="alpha-sources-label">&#128196; 支撑来源</div>' +
          sources.map(function(s) {{
            return '<div class="alpha-source-item">' +
              (s.url ? '<a href="' + escapeAttr(s.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(s.title || s.url) + '</a>' : '<span style="color:#c4b5fd">' + escapeHtml(s.title || '') + '</span>') +
              (s.why ? '<span class="alpha-source-why">&mdash; ' + escapeHtml(s.why) + '</span>' : '') +
              '</div>';
          }}).join('') + '</div>' : '') +
        '<div style="margin-top:12px;font-size:10px;color:#6b7280">由 ' + escapeHtml(a.model || 'deepseek-reasoner') + ' 生成 &middot; ' + escapeHtml(a.generated_at || '') + '</div>' +
        '</div>';
    }}

    // ── Hero section ──────────────────────────────────────────────────────────
    function renderHero(dayItems) {{
      const top3 = dayItems.slice(0, 3);
      if (!top3.length) return '';
      return '<div class="hero-section">' +
        '<div class="hero-label">今日精选 TOP ' + top3.length + '</div>' +
        '<div class="hero-grid">' + top3.map(function(item, i) {{ return heroCard(item, i + 1); }}).join('') + '</div>' +
        '</div>';
    }}

    function heroCard(item, rank) {{
      const section = (item.report_sections || [])[0] || '';
      return '<article class="hero-card" data-section="' + escapeAttr(section) + '">' +
        '<div class="hero-rank">' + rank + '</div>' +
        '<h4>' + highlight(item.display_title || item.title, state.q) + '</h4>' +
        '<div class="meta">' +
        '<span class="tag">' + escapeHtml((item.report_section_labels || [])[0] || '其他') + '</span>' +
        '<span class="tag">' + escapeHtml(categoryLabel(item.category)) + '</span>' +
        '</div>' +
        '<p class="summary">' + highlight(item.tldr || item.one_line_summary || '', state.q) + '</p>' +
        referenceHtml(item) +
        '</article>';
    }}

    // ── Boot ──────────────────────────────────────────────────────────────────
    boot();

    // Handle hash-based tab routing
    (function() {{
      const hash = location.hash.slice(1);
      if (hash === 'notes' || hash === 'weekly') {{ switchTab(hash); }}
    }})();

    // Onboarding
    const OB_KEY = 'samson_quant_onboarded_v2';
    function showOnboarding() {{ $('ob-overlay').classList.remove('hidden'); }}
    function hideOnboarding() {{
      $('ob-overlay').classList.add('hidden');
      localStorage.setItem(OB_KEY, '1');
      const hint = $('section-hint');
      if (hint) hint.style.display = 'none';
    }}
    $('ob-dismiss').addEventListener('click', hideOnboarding);
    $('ob-overlay').addEventListener('click', function(e) {{
      if (e.target === $('ob-overlay')) hideOnboarding();
    }});
    $('help-btn').addEventListener('click', showOnboarding);
    if (!localStorage.getItem(OB_KEY)) {{
      showOnboarding();
    }} else {{
      const hint = $('section-hint');
      if (hint) hint.style.display = 'none';
    }}
  </script>
</body>
</html>
"""


def _section_counts_from_field(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for key in (row.get("report_sections") or []):
            if key != "other":
                counts[key] = counts.get(key, 0) + 1
    return counts


def _with_display_labels(row: dict[str, Any]) -> dict[str, Any]:
    enriched = with_reader_format(row)
    enriched["report_sections"] = row_section_keys(row)
    enriched["report_section_labels"] = row_section_labels(row)
    enriched["category_label"] = category_zh(str(row.get("category", "")))
    enriched["priority_label"] = priority_zh(str(row.get("read_priority", "")))
    enriched["source_type_label"] = source_type_zh(str(row.get("source_type", "")))
    return enriched


def _day(row: dict[str, Any]) -> str:
    return str(row.get("collected_at", ""))[:10] or "unknown"
