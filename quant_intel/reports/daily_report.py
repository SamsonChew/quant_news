from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from quant_intel.i18n import category_zh, priority_zh, source_type_zh
from quant_intel.models import utc_now_iso
from quant_intel.reports.reader_format import (
    core_value,
    display_title,
    key_points,
    reference_url,
    tldr,
)
from quant_intel.reports.sections import REPORT_SECTIONS, row_section_keys, rows_for_section


PRIMARY_SOURCE_BUCKETS = ("arxiv", "zhihu", "quantml", "forum")


def select_report_rows(
    rows: list[dict[str, Any]], report_config: dict[str, int]
) -> list[dict[str, Any]]:
    max_per_section = int(report_config["max_items_per_category"])
    max_total = int(report_config["max_total_items"])
    main_section_keys = {section.key for section in REPORT_SECTIONS}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["final_score"], reverse=True):
        if not is_primary_source(row):
            continue
        sections = [key for key in row_section_keys(row) if key in main_section_keys]
        if not sections:
            continue
        grouped[sections[0]].append(row)

    selected: list[dict[str, Any]] = []
    for section in REPORT_SECTIONS:
        selected.extend(_select_diverse_by_source(grouped[section.key], max_per_section))

    selected.sort(key=lambda r: r["final_score"], reverse=True)
    return selected[:max_total]


def select_history_rows(
    rows: list[dict[str, Any]], report_config: dict[str, int]
) -> list[dict[str, Any]]:
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        day = str(row.get("collected_at", ""))[:10] or "unknown"
        by_day[day].append(row)

    selected: list[dict[str, Any]] = []
    for day in sorted(by_day, reverse=True):
        selected.extend(select_report_rows(by_day[day], report_config))

    return selected


def _select_diverse_by_source(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if not rows:
        return []

    sorted_rows = sorted(rows, key=lambda row: row["final_score"], reverse=True)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted_rows:
        buckets[source_bucket(row)].append(row)

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for bucket in PRIMARY_SOURCE_BUCKETS:
        for row in buckets.get(bucket, []):
            if row["id"] in seen_ids:
                continue
            selected.append(row)
            seen_ids.add(row["id"])
            break
        if len(selected) >= limit:
            return selected

    per_bucket_cap = max(1, limit // 2)
    bucket_counts: dict[str, int] = defaultdict(int)
    for row in selected:
        bucket_counts[source_bucket(row)] += 1

    for row in sorted_rows:
        if row["id"] in seen_ids:
            continue
        bucket = source_bucket(row)
        if bucket_counts[bucket] >= per_bucket_cap and len(selected) < limit - 1:
            continue
        selected.append(row)
        seen_ids.add(row["id"])
        bucket_counts[bucket] += 1
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for row in sorted_rows:
            if row["id"] in seen_ids:
                continue
            selected.append(row)
            seen_ids.add(row["id"])
            if len(selected) >= limit:
                break

    return selected[:limit]


def is_primary_source(row: dict[str, Any]) -> bool:
    return source_bucket(row) in PRIMARY_SOURCE_BUCKETS


def source_bucket(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "").lower()
    source_type = str(row.get("source_type") or "").lower()
    if source_type == "quantml" or "quantml" in source:
        return "quantml"
    if source_type == "zhihu" or "知乎" in str(row.get("source") or ""):
        return "zhihu"
    if source_type == "forum":
        return "forum"
    if source == "arxiv" or source_type == "paper":
        return "arxiv"
    return "other"


def build_alpha_section(alpha_md: str) -> list[str]:
    if not alpha_md:
        return []
    return ["## 今日 Alpha Idea", "", alpha_md, ""]


def build_daily_report(
    rows: list[dict[str, Any]],
    report_date: str,
    output_dir: Path,
    report_config: dict[str, int],
    source_stats: dict[str, int],
    alpha_md: str = "",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = select_report_rows(rows, report_config)
    executive_limit = int(report_config["executive_brief_items"])

    lines: list[str] = []
    lines.append(f"# 每日量化情报报告 - {report_date}")
    lines.append("")
    lines.append(f"生成时间：{utc_now_iso()}")

    # Alpha idea goes right at the top, before everything else
    if alpha_md:
        lines.append("")
        lines.extend(build_alpha_section(alpha_md))

    lines.append("")
    lines.append("## 执行摘要")
    lines.append("")
    if selected:
        for idx, row in enumerate(selected[:executive_limit], start=1):
            lines.extend(_format_numbered_item(idx, row))
            lines.append("")
    else:
        lines.append("今天没有收集到达到展示标准的高质量内容。")

    max_per_section = int(report_config["max_items_per_category"])
    lines.append("")
    lines.append("## 两条主线")
    lines.append("")
    has_section = False
    for section in REPORT_SECTIONS:
        section_rows = rows_for_section(selected, section, max_per_section)
        if not section_rows:
            continue
        has_section = True
        lines.append(f"### {section.label}")
        lines.append("")
        lines.append(section.description)
        lines.append("")
        for row in section_rows:
            lines.extend(_format_compact_item(row))
            lines.append("")
    if not has_section:
        lines.append("暂无可展示的分区内容。")

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        by_category[row["category"]].append(row)

    lines.append("")
    lines.append("## 细分标签详情")
    lines.append("")
    for category in sorted(by_category):
        lines.append(f"### {category_zh(category)}")
        lines.append("")
        for row in by_category[category]:
            lines.extend(_format_item(row))
            lines.append("")

    lines.append("## 来源统计")
    lines.append("")
    if source_stats:
        for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- 暂无来源统计。")

    report_path = output_dir / f"{report_date}.md"
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def _format_item(row: dict[str, Any]) -> list[str]:
    lines = [
        f"#### {_escape(display_title(row))}",
        "",
        f"- 来源：{row['source']}（{source_type_zh(row['source_type'])}）",
        f"- 优先级：{priority_zh(row['read_priority'])}",
        f"- 评分：{row['final_score']:.2f}",
        "",
        f"1. 这篇文章的太长不读：{tldr(row)}",
        f"2. 核心价值，对我量化的工作能够提供什么样的帮助：{core_value(row)}",
        f"3. 关键核心点 / 论文或帖子摘要：{_inline_points(row)}",
        f"4. 原文链接：{_reference_markdown(row)}",
    ]
    figures = str(row.get("key_figures_md") or "").strip()
    if figures:
        lines.append("")
        lines.append("**关键图表：**")
        lines.append(figures)
    return lines


def _format_compact_item(row: dict[str, Any]) -> list[str]:
    lines = [
        f"- **{_escape(display_title(row))}**",
        f"  - 来源：{row['source']}（{source_type_zh(row['source_type'])}）",
        f"  - 优先级：{priority_zh(row['read_priority'])}，评分：{row['final_score']:.2f}",
        f"  - 1. 这篇文章的太长不读：{tldr(row)}",
        f"  - 2. 核心价值，对我量化的工作能够提供什么样的帮助：{core_value(row)}",
        f"  - 3. 关键核心点 / 论文或帖子摘要：{_inline_points(row)}",
        f"  - 4. 原文链接：{_reference_markdown(row)}",
    ]
    figures = str(row.get("key_figures_md") or "").strip()
    if figures:
        for fig_line in figures.splitlines():
            lines.append(f"  - {fig_line}")
    return lines


def _format_numbered_item(idx: int, row: dict[str, Any]) -> list[str]:
    return [
        f"{idx}. **{_escape(display_title(row))}** ({category_zh(row['category'])}，评分 {row['final_score']:.2f})",
        f"   1. 这篇文章的太长不读：{tldr(row)}",
        f"   2. 核心价值，对我量化的工作能够提供什么样的帮助：{core_value(row)}",
        f"   3. 关键核心点 / 论文或帖子摘要：{_inline_points(row)}",
        f"   4. 原文链接：{_reference_markdown(row)}",
    ]


def _inline_points(row: dict[str, Any]) -> str:
    return "；".join(key_points(row))


def _reference_markdown(row: dict[str, Any]) -> str:
    url = reference_url(row)
    if not url:
        return "暂无可打开链接"
    return f"[{url}]({url})"


def _escape(value: str) -> str:
    return value.replace("|", "\\|")
