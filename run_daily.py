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
from quant_intel.models import Item, Score, utc_now_iso
from quant_intel.pipeline.classify import classify_item
from quant_intel.pipeline.normalize import canonical_url, dedup_by_title
from quant_intel.pipeline.score import score_item
from quant_intel.pipeline.summarize import summarize_item, summary_from_llm_payload
from quant_intel.reports import build_daily_report, build_home_dashboard
from quant_intel.reports import build_html_dashboard
from quant_intel.notes.reader import load_notes
from quant_intel.reports.crypto_alpha import load_alpha_history, save_crypto_alpha
from quant_intel.reports.daily_report import select_history_rows, select_report_rows, build_alpha_section
from quant_intel.reports.sections import row_section_keys
from quant_intel.reports.weekly_loader import load_weekly_reports
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
            rule_summary.model_name = "deepseek:skipped"  # marks intentional non-quant skip
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


def rescan_summaries(db: "Database", client: "DeepSeekClient", max_items: int, only_date: str = "") -> int:
    """Re-summarize existing items that only have rule-based summaries, by score desc."""
    import json
    if only_date:
        rows = db.conn.execute(
            """
            SELECT i.id, i.source, i.source_type, i.title, i.url,
                   i.authors, i.published_at, i.collected_at, i.raw_text,
                   i.abstract, i.content_hash, i.category, i.tags, i.language, i.metadata,
                   sc.relevance_score, sc.novelty_score, sc.academic_score,
                   sc.discussion_score, sc.actionable_score, sc.final_score, sc.created_at AS score_at
            FROM items i
            JOIN summaries s ON s.item_id = i.id
            JOIN scores sc ON sc.item_id = i.id
            WHERE s.prompt_version != ? AND substr(i.collected_at, 1, 10) = ?
            ORDER BY sc.final_score DESC
            LIMIT ?
            """,
            (PROMPT_VERSION, only_date, max_items),
        ).fetchall()
    else:
        rows = db.conn.execute(
            """
            SELECT i.id, i.source, i.source_type, i.title, i.url,
                   i.authors, i.published_at, i.collected_at, i.raw_text,
                   i.abstract, i.content_hash, i.category, i.tags, i.language, i.metadata,
                   sc.relevance_score, sc.novelty_score, sc.academic_score,
                   sc.discussion_score, sc.actionable_score, sc.final_score, sc.created_at AS score_at
            FROM items i
            JOIN summaries s ON s.item_id = i.id
            JOIN scores sc ON sc.item_id = i.id
            WHERE s.prompt_version != ?
            ORDER BY sc.final_score DESC
            LIMIT ?
            """,
            (PROMPT_VERSION, max_items),
        ).fetchall()

    print(f"[rescan] {len(rows)} items need re-summarization (top {max_items} by score)")
    updated = 0
    for row in rows:
        def _j(v):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return []
            return v or []

        item = Item(
            id=row["id"], source=row["source"], source_type=row["source_type"],
            title=row["title"], url=row["url"],
            authors=_j(row["authors"]), published_at=row["published_at"] or "",
            collected_at=row["collected_at"] or "", raw_text=row["raw_text"] or "",
            abstract=row["abstract"] or "", content_hash=row["content_hash"] or "",
            category=row["category"] or "Unclassified",
            tags=_j(row["tags"]), language=row["language"] or "en",
            metadata=_j(row["metadata"]) if isinstance(_j(row["metadata"]), dict) else {},
        )
        score = Score(
            item_id=row["id"],
            relevance_score=float(row["relevance_score"] or 0),
            novelty_score=float(row["novelty_score"] or 0),
            academic_score=float(row["academic_score"] or 0),
            discussion_score=float(row["discussion_score"] or 0),
            actionable_score=float(row["actionable_score"] or 0),
            final_score=float(row["final_score"] or 0),
            created_at=row["score_at"] or "",
        )
        summary, skipped, called = summarize_for_run(item, score, client, rescore_all=True)
        db.upsert_summary(summary)
        updated += 1
        status = "skip" if skipped else ("ok" if called else "rule")
        print(f"[rescan] {updated}/{len(rows)} [{status}] {item.title[:70]}")
    return updated


def run(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)

    db = Database(args.db)
    db.init_schema()

    source_config = load_sources_config()
    scoring_config = load_scoring_config()
    report_config = load_report_config()
    sources = build_sources(source_config, sample=args.sample)
    summary_client = build_summary_client(args.summary_provider)

    if args.rescan_summaries > 0:
        if summary_client is None:
            print("[rescan] skipped — no DeepSeek client available")
        else:
            # Default to today — never touch previous days unless explicitly overridden
            target_date = args.rescan_date or args.report_date
            rescan_summaries(db, summary_client, args.rescan_summaries, only_date=target_date)

        # Rebuild HTML with updated summaries
        today = date.fromisoformat(args.report_date)
        today_rows = db.fetch_report_rows(args.report_date)
        today_selected = select_report_rows(today_rows, report_config)
        today_stats = dict(Counter(str(r.get("source", "Unknown")) for r in today_selected))
        build_daily_report(
            rows=today_rows,
            report_date=args.report_date,
            output_dir=args.output_dir,
            report_config=report_config,
            source_stats=today_stats,
        )
        build_html_dashboard(
            rows=today_rows,
            report_date=args.report_date,
            output_dir=args.output_dir,
            report_config=report_config,
            source_stats=today_stats,
        )
        start_date = (today - timedelta(days=args.history_days - 1)).isoformat()
        history_rows = db.fetch_rows_between(start_date, args.report_date)
        history_rows = select_history_rows(history_rows, report_config)
        history_stats = dict(Counter(str(r.get("source", "Unknown")) for r in history_rows))
        alpha_history = load_alpha_history(args.output_dir)
        notes = load_notes(Path("notes"))
        weekly_reports = load_weekly_reports(
            Path("/Users/samsonchew/Desktop/Quant/weekly_report")
        )
        home_path = build_home_dashboard(
            rows=history_rows,
            end_date=args.report_date,
            history_days=args.history_days,
            output_dir=args.output_dir,
            report_config=report_config,
            source_stats=history_stats,
            alpha_history=alpha_history,
            notes=notes,
            weekly_reports=weekly_reports,
        )
        print(f"[rescan] HTML rebuilt → {home_path}")
        db.close()
        return 0

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

            # Skip if another item with the same canonical URL is already in DB
            if db.get_item_id_by_canonical_url(item.url):
                existing_id = db.get_item_id_by_canonical_url(item.url)
                if existing_id and existing_id != item.id:
                    continue  # arXiv duplicate from different URL form — already processed

            if not db.upsert_item(item):
                # Already seen in a previous run — skip to avoid cross-day duplicates
                continue
            stored += 1
            db.upsert_score(score)

            # Always call DeepSeek when client is available — no cap
            summary, skipped, _ = summarize_for_run(
                item, score, summary_client, db=db, rescore_all=args.rescore_all
            )
            db.upsert_summary(summary)

            if not skipped:
                run_item_ids.append(item.id)

    # Auto-rescan today's articles that got rule-based summaries (DeepSeek failures, etc.)
    if summary_client is not None:
        rescan_summaries(db, summary_client, max_items=200, only_date=args.report_date)

    rows = db.fetch_report_rows_by_ids(run_item_ids)

    # Blend feedback adjustments into final_score before selection
    for row in rows:
        signal = db.get_feedback(row["id"])
        if signal:
            adj = 1.5 if signal > 0 else -2.0
            row["final_score"] = round(max(0.0, min(10.0, row["final_score"] + adj)), 3)

    # Title-similarity dedup: drop near-duplicate articles before section selection
    rows = dedup_by_title(rows)

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
    notes = load_notes(Path("notes"))
    weekly_reports = load_weekly_reports(
        Path("/Users/samsonchew/Desktop/Quant/weekly_report")
    )
    home_path = build_home_dashboard(
        rows=history_rows,
        end_date=args.report_date,
        history_days=args.history_days,
        output_dir=args.output_dir,
        report_config=report_config,
        source_stats=history_stats,
        alpha_history=alpha_history,
        notes=notes,
        weekly_reports=weekly_reports,
    )
    db.close()

    print(f"Fetched: {sum(fetched_count.values())}")
    print(f"Stored items: {stored}")
    print(f"Report items: {len(selected_rows)}")
    print(f"Report: {report_path}")
    print(f"Dashboard: {dashboard_path}")
    print(f"Home: {home_path}")

    _deploy_to_github(args.output_dir, args.report_date)
    return 0


def _deploy_to_github(output_dir: Path, report_date: str) -> None:
    """Generate static JSON files and push to gh-pages if git remote is configured."""
    import subprocess

    git_dir = output_dir / ".git"
    if not git_dir.exists():
        return  # no git repo in output dir — skip silently

    print("[deploy] Generating static JSON files...")
    try:
        from build_static import build_static
        build_static(output_dir=output_dir)
    except Exception as exc:
        print(f"[deploy] build_static failed: {exc}")
        return

    try:
        subprocess.run(["git", "-C", str(output_dir), "add", "-A"], check=True)
        result = subprocess.run(
            ["git", "-C", str(output_dir), "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            print("[deploy] Nothing changed — skipping push")
            return
        subprocess.run(
            ["git", "-C", str(output_dir), "commit", "-m", f"Update {report_date}"],
            check=True,
        )
        subprocess.run(["git", "-C", str(output_dir), "push"], check=True)
        print(f"[deploy] Pushed → https://samsonchew.github.io/quant-intel/")
    except subprocess.CalledProcessError as exc:
        print(f"[deploy] git push failed: {exc}")


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
        "--rescan-summaries",
        type=int,
        default=0,
        metavar="N",
        help="Re-summarize up to N rule_v1 items with DeepSeek (defaults to today only). Skips normal fetch.",
    )
    parser.add_argument(
        "--rescan-date",
        default="",
        metavar="YYYY-MM-DD",
        help="Override date for --rescan-summaries (default: today). Use carefully to avoid touching old articles.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
