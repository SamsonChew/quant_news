#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from quant_intel.config import (
    load_report_config,
    load_scoring_config,
    load_sources_config,
)
from quant_intel.env import load_env_file
from quant_intel.llm import DeepSeekClient
from quant_intel.llm.deepseek import PROMPT_VERSION
from quant_intel.models import utc_now_iso
from quant_intel.pipeline.classify import classify_item
from quant_intel.pipeline.normalize import canonical_url
from quant_intel.pipeline.score import score_item
from quant_intel.pipeline.summarize import summarize_item, summary_from_llm_payload
from quant_intel.reports import build_daily_report, build_home_dashboard
from quant_intel.reports import build_html_dashboard
from quant_intel.reports.crypto_alpha import load_alpha_history, save_crypto_alpha
from quant_intel.reports.daily_report import select_history_rows, select_report_rows, build_alpha_section
from quant_intel.reports.sections import row_section_keys
from quant_intel.sources import ArxivSource, GitHubSource, LocalJsonSource
from quant_intel.sources import QuantMLSource, RSSSource, SampleSource, ZhihuSource
from quant_intel.storage import Database


def build_sources(config: dict, sample: bool) -> list:
    if sample:
        return [SampleSource()]

    sources = []
    arxiv_cfg = config.get("arxiv", {})
    if arxiv_cfg.get("enabled", False):
        sources.append(
            ArxivSource(
                queries=arxiv_cfg.get("queries", []),
                max_results=int(arxiv_cfg.get("max_results", 15)),
                delay_seconds=float(arxiv_cfg.get("delay_seconds", 3.2)),
            )
        )

    quantml_cfg = config.get("quantml", {})
    if quantml_cfg.get("enabled", False):
        sources.append(
            QuantMLSource(
                url=quantml_cfg.get("url", "https://www.quantml.cn/"),
                max_results=int(quantml_cfg.get("max_results", 8)),
            )
        )

    github_cfg = config.get("github", {})
    if github_cfg.get("enabled", False):
        sources.append(
            GitHubSource(
                queries=github_cfg.get("queries", []),
                max_results=int(github_cfg.get("max_results", 15)),
            )
        )

    rss_cfg = config.get("rss", {})
    if rss_cfg.get("enabled", False):
        sources.append(
            RSSSource(
                feeds=rss_cfg.get("feeds", []),
                max_results_per_feed=int(rss_cfg.get("max_results_per_feed", 10)),
            )
        )

    social_cfg = config.get("social_json", {})
    if social_cfg.get("enabled", False):
        sources.append(LocalJsonSource(paths=social_cfg.get("paths", [])))

    zhihu_cfg = config.get("zhihu", {})
    if zhihu_cfg.get("enabled", False):
        sources.append(
            ZhihuSource(
                topics=zhihu_cfg.get("topics", []),
                columns=zhihu_cfg.get("columns", []),
                max_results_per_topic=int(zhihu_cfg.get("max_results_per_topic", 5)),
            )
        )

    return sources


def build_summary_client(provider: str) -> DeepSeekClient | None:
    if provider == "rule":
        print("[info] Summary provider: rule-based")
        return None

    client = DeepSeekClient.from_env()
    if client is None:
        if provider == "deepseek":
            print("[warn] DEEPSEEK_API_KEY not set; falling back to rule-based summary")
        else:
            print("[info] Summary provider: rule-based (DEEPSEEK_API_KEY not set)")
        return None

    print(f"[info] Summary provider: DeepSeek ({client.config.model})")
    return client


def summarize_for_run(
    item,
    score,
    client: DeepSeekClient | None,
    db: Database | None = None,
    rescore_all: bool = False,
):
    # Returns (summary, skipped, called_api)
    # skipped=True  → DeepSeek said non-quant, use rule fallback
    # called_api=True → an actual DeepSeek API call was made (counts against cap)
    if client is None:
        return summarize_item(item, score), False, False

    # Return cached summary without calling the API
    if not rescore_all and db is not None:
        existing = db.get_summary(item.id)
        if existing and existing.get("prompt_version") == PROMPT_VERSION:
            from quant_intel.models import Summary
            return Summary(
                item_id=existing["item_id"],
                one_line_summary=existing["one_line_summary"],
                technical_summary=existing["technical_summary"],
                key_points=existing["key_points"] if isinstance(existing["key_points"], list) else [],
                quant_relevance=existing["quant_relevance"],
                possible_use_case=existing["possible_use_case"],
                limitations=existing["limitations"],
                read_priority=existing["read_priority"],
                model_name=existing["model_name"],
                created_at=existing["created_at"],
                key_figures_md=existing.get("key_figures_md", ""),
                prompt_version=existing["prompt_version"],
            ), False, False  # cache hit — no API call

    try:
        payload = client.summarize(item, score)
        if payload.get("skip"):
            rule_summary = summarize_item(item, score)
            rule_summary.prompt_version = PROMPT_VERSION
            return rule_summary, True, True  # API called, content skipped as non-quant
        return summary_from_llm_payload(
            item=item,
            score=score,
            payload=payload,
            model_name=f"deepseek:{client.config.model}",
            prompt_version=PROMPT_VERSION,
        ), False, True  # API called successfully
    except Exception as exc:
        print(
            "[warn] DeepSeek summary failed; using rule-based summary: "
            f"{item.title[:90]}: {exc}"
        )
        return summarize_item(item, score), False, False  # API failed, don't count


def _print_section_breakdown(all_rows: list, selected_rows: list) -> None:
    counts: dict[str, int] = {}
    for row in all_rows:
        for key in row_section_keys(row):
            counts[key] = counts.get(key, 0) + 1
    selected_ids = {row["id"] for row in selected_rows}
    section_order = ["deep_learning_quant", "ai_quant_tools", "daily_news", "other"]
    parts = []
    for key in section_order:
        n = counts.get(key, 0)
        if n:
            label = f"{key}(dropped)" if key == "other" else key
            parts.append(f"{label}: {n}")
    print(f"[sections] {' | '.join(parts)}")
    other_rows = [r for r in all_rows if row_section_keys(r) == ["other"]]
    if other_rows:
        top = sorted(other_rows, key=lambda r: r.get("final_score", 0), reverse=True)[:3]
        print("[sections] other 分桶最高分前 3（可能需要调整关键词）:")
        for r in top:
            print(f"  {r.get('final_score', 0):.2f}  [{r.get('category', '')}]  {r.get('title', '')[:80]}")


def run(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)

    db = Database(args.db)
    db.init_schema()

    source_config = load_sources_config()
    scoring_config = load_scoring_config()
    report_config = load_report_config()
    sources = build_sources(source_config, sample=args.sample)
    summary_client = build_summary_client(args.summary_provider)

    fetched_count = Counter()
    stored = 0
    run_item_ids: list[str] = []
    today = date.fromisoformat(args.report_date)
    deepseek_calls = 0
    max_deepseek = args.max_deepseek_items

    for source in sources:
        try:
            items = source.fetch()
        except Exception as exc:
            print(f"[warn] source failed: {source.name}: {exc}")
            continue

        fetched_count[source.name] += len(items)
        for item in items:
            item = classify_item(item)
            score = score_item(item, scoring_config, today=today)

            # TODO 2: skip if another item with the same canonical URL is already in DB
            if db.get_item_id_by_canonical_url(item.url):
                existing_id = db.get_item_id_by_canonical_url(item.url)
                if existing_id and existing_id != item.id:
                    run_item_ids.append(existing_id)
                    continue

            if not db.upsert_item(item):
                continue
            stored += 1
            db.upsert_score(score)

            use_llm = summary_client is not None and (max_deepseek <= 0 or deepseek_calls < max_deepseek)
            summary, skipped, called_api = summarize_for_run(
                item, score, summary_client if use_llm else None, db=db, rescore_all=args.rescore_all
            )
            if called_api:
                deepseek_calls += 1
            db.upsert_summary(summary)

            if not skipped:
                run_item_ids.append(item.id)

    rows = db.fetch_report_rows_by_ids(run_item_ids)

    # TODO 3: blend feedback adjustments into final_score before selection
    for row in rows:
        signal = db.get_feedback(row["id"])
        if signal:
            adj = 1.5 if signal > 0 else -2.0
            row["final_score"] = round(max(0.0, min(10.0, row["final_score"] + adj)), 3)

    selected_rows = select_report_rows(rows, report_config)

    # TODO 4: print section breakdown so dropped items are visible
    _print_section_breakdown(rows, selected_rows)
    source_stats = dict(Counter(str(row.get("source", "Unknown")) for row in selected_rows))

    alpha_md = ""
    if summary_client is not None and selected_rows:
        try:
            alpha_md = summary_client.generate_alpha_ideas(selected_rows)
        except Exception as exc:
            print(f"[warn] Alpha ideas generation failed: {exc}")

    if summary_client is not None and rows:
        try:
            print("[info] Generating daily crypto alpha idea...")
            crypto_alpha = summary_client.generate_daily_crypto_alpha(rows, args.report_date)
            alpha_path = save_crypto_alpha(crypto_alpha, args.report_date, args.output_dir)
            print(f"[info] Crypto alpha saved: {alpha_path}")
        except Exception as exc:
            print(f"[warn] Crypto alpha generation failed: {exc}")

    report_path = build_daily_report(
        rows=rows,
        report_date=args.report_date,
        output_dir=args.output_dir,
        report_config=report_config,
        source_stats=source_stats,
        alpha_md=alpha_md,
    )
    dashboard_path = build_html_dashboard(
        rows=rows,
        report_date=args.report_date,
        output_dir=args.output_dir,
        report_config=report_config,
        source_stats=source_stats,
    )
    db.insert_report(
        report_date=args.report_date,
        report_path=str(report_path),
        generated_at=utc_now_iso(),
        item_count=len(selected_rows),
        source_stats=source_stats,
    )

    start_date = (today - timedelta(days=args.history_days - 1)).isoformat()
    history_rows = db.fetch_rows_between(start_date, args.report_date)
    history_rows = select_history_rows(history_rows, report_config)
    history_stats = dict(Counter(str(row.get("source", "Unknown")) for row in history_rows))
    alpha_history = load_alpha_history(args.output_dir)
    home_path = build_home_dashboard(
        rows=history_rows,
        end_date=args.report_date,
        history_days=args.history_days,
        output_dir=args.output_dir,
        report_config=report_config,
        source_stats=history_stats,
        alpha_history=alpha_history,
    )
    db.close()

    print(f"Fetched: {sum(fetched_count.values())}")
    print(f"Stored items: {stored}")
    print(f"Report items: {len(selected_rows)}")
    print(f"Report: {report_path}")
    print(f"Dashboard: {dashboard_path}")
    print(f"Home: {home_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily quant intelligence pipeline")
    parser.add_argument("--db", type=Path, default=Path("data/quant_intel.sqlite"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/daily"))
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--history-days", type=int, default=7)
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run with deterministic sample items instead of live sources.",
    )
    parser.add_argument(
        "--summary-provider",
        choices=("auto", "rule", "deepseek"),
        default="auto",
        help="Summary backend: auto uses DeepSeek when DEEPSEEK_API_KEY is set.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Optional env file for DEEPSEEK_API_KEY and related settings.",
    )
    parser.add_argument(
        "--rescore-all",
        action="store_true",
        help=f"Force re-summarise all items even if already at prompt version {PROMPT_VERSION}.",
    )
    parser.add_argument(
        "--max-deepseek-items",
        type=int,
        default=0,
        help="Cap DeepSeek API calls per run (0 = unlimited). Remaining items use rule-based summary.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
