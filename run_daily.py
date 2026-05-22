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
from quant_intel.models import utc_now_iso
from quant_intel.pipeline.classify import classify_item
from quant_intel.pipeline.score import score_item
from quant_intel.pipeline.summarize import summarize_item, summary_from_llm_payload
from quant_intel.reports import build_daily_report, build_home_dashboard
from quant_intel.reports import build_html_dashboard
from quant_intel.reports.daily_report import select_history_rows, select_report_rows, build_alpha_section
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


def summarize_for_run(item, score, client: DeepSeekClient | None):
    if client is None:
        return summarize_item(item, score), False  # (summary, skipped)

    try:
        payload = client.summarize(item, score)
        if payload.get("skip"):
            return summarize_item(item, score), True
        return summary_from_llm_payload(
            item=item,
            score=score,
            payload=payload,
            model_name=f"deepseek:{client.config.model}",
        ), False
    except Exception as exc:
        print(
            "[warn] DeepSeek summary failed; using rule-based summary: "
            f"{item.title[:90]}: {exc}"
        )
        return summarize_item(item, score), False


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

            if not db.upsert_item(item):
                continue
            stored += 1
            db.upsert_score(score)

            summary, skipped = summarize_for_run(item, score, summary_client)
            db.upsert_summary(summary)

            if not skipped:
                run_item_ids.append(item.id)

    rows = db.fetch_report_rows_by_ids(run_item_ids)
    selected_rows = select_report_rows(rows, report_config)
    source_stats = dict(Counter(str(row.get("source", "Unknown")) for row in selected_rows))

    alpha_md = ""
    if summary_client is not None and selected_rows:
        try:
            alpha_md = summary_client.generate_alpha_ideas(selected_rows)
        except Exception as exc:
            print(f"[warn] Alpha ideas generation failed: {exc}")

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
    home_path = build_home_dashboard(
        rows=history_rows,
        end_date=args.report_date,
        history_days=args.history_days,
        output_dir=args.output_dir,
        report_config=report_config,
        source_stats=history_stats,
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
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
