from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportSection:
    key: str
    label: str
    description: str
    categories: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    require_keyword: bool = False


REPORT_SECTIONS = (
    ReportSection(
        key="deep_learning_quant",
        label="深度学习量化未来",
        description="技术主线：只看深度学习、强化学习、Transformer、图神经网络、表征学习、订单簿预测、金融时间序列大模型等在量化里的应用。这个频道用于给老板快速判断“未来在哪里”。",
        source_types=("paper", "forum", "blog", "news", "social", "zhihu", "x", "quantml"),
        keywords=(
            "deep learning",
            "neural",
            "transformer",
            "attention layer",
            "attention layers",
            "self-attention",
            "reinforcement learning",
            "deep reinforcement",
            "representation learning",
            "sequence model",
            "time series foundation model",
            "foundation model",
            "graph neural",
            "gnn",
            "lstm",
            "gru",
            "temporal fusion",
            "limit order book",
            "order book prediction",
            "深度学习",
            "神经网络",
            "强化学习",
            "深度强化学习",
            "时间序列大模型",
            "金融大模型",
            "订单簿预测",
            "表征学习",
        ),
        require_keyword=True,
    ),
    ReportSection(
        key="ai_quant_tools",
        label="AI 量化工具",
        description="工具主线：只看能提升量化研究效率的 AI 工具、代码仓库、研究自动化、智能体、回测/数据工程工具和可接入团队工作流的基础设施。",
        categories=("LLM / Agents for Quant", "Backtesting / Research Tools", "Data Engineering"),
        source_types=("github", "quantml"),
        keywords=(
            "ai",
            "llm",
            "agent",
            "agents",
            "copilot",
            "deepseek",
            "openai",
            "research automation",
            "workflow",
            "toolkit",
            "library",
            "repository",
            "github",
            "api",
            "backtest",
            "backtesting",
            "dataset",
            "data pipeline",
            "feature store",
            "monitor",
            "智能体",
            "大模型",
            "研究自动化",
            "工具",
            "代码库",
            "回测",
            "数据流水线",
        ),
    ),
)


def row_section_keys(row: dict[str, Any]) -> list[str]:
    # The product intentionally has only two main lanes. Keep them mutually
    # exclusive so the UI reads like a clear boss-facing map: 技术 vs 工具.
    if _matches_section(row, "ai_quant_tools") and _is_tool_row(row) and _has_quant_context(row):
        return ["ai_quant_tools"]
    if _matches_section(row, "deep_learning_quant") and _has_quant_context(row):
        return ["deep_learning_quant"]
    if _matches_section(row, "ai_quant_tools") and _has_quant_context(row):
        return ["ai_quant_tools"]
    return ["other"]


def row_section_labels(row: dict[str, Any]) -> list[str]:
    key_to_label = {section.key: section.label for section in REPORT_SECTIONS}
    return [key_to_label.get(key, "其他") for key in row_section_keys(row)]


def section_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for key in row_section_keys(row):
            counts[key] = counts.get(key, 0) + 1
    return counts


def rows_for_section(
    rows: list[dict[str, Any]], section: ReportSection, limit: int
) -> list[dict[str, Any]]:
    matched = [
        row
        for row in rows
        if section.key in row_section_keys(row)
    ]
    return sorted(matched, key=lambda row: row["final_score"], reverse=True)[:limit]


def _matches_section(row: dict[str, Any], section_key: str) -> bool:
    section = next((item for item in REPORT_SECTIONS if item.key == section_key), None)
    if section is None:
        return False
    category = str(row.get("category", ""))
    source_type = str(row.get("source_type", ""))
    category_match = category in section.categories
    source_type_match = source_type in section.source_types
    keyword_match = _matches_keywords(row, section.keywords)
    if section.require_keyword:
        return keyword_match and (
            category_match
            or source_type_match
            or (not section.categories and not section.source_types)
        )
    return category_match or source_type_match or keyword_match


def _is_tool_row(row: dict[str, Any]) -> bool:
    category = str(row.get("category", ""))
    source_type = str(row.get("source_type", ""))
    if source_type == "github":
        return True
    if category in {"LLM / Agents for Quant", "Backtesting / Research Tools", "Data Engineering"}:
        return True
    return _matches_keywords(
        row,
        (
            "research automation",
            "workflow",
            "toolkit",
            "library",
            "repository",
            "github",
            "api",
            "benchmark code",
            "data pipeline",
            "智能体",
            "研究自动化",
            "工具",
            "代码库",
        ),
    )


def _has_quant_context(row: dict[str, Any]) -> bool:
    return _matches_keywords(
        row,
        (
            "quant",
            "trading",
            "trade",
            "finance",
            "financial",
            "market",
            "portfolio",
            "alpha",
            "risk",
            "asset",
            "equity",
            "equities",
            "futures",
            "order book",
            "price",
            "prices",
            "return",
            "returns",
            "volatility",
            "option",
            "backtest",
            "execution",
            "strategy",
            "factor",
            "crypto",
            "量化",
            "交易",
            "金融",
            "市场",
            "组合",
            "风险",
            "资产",
            "收益",
            "波动率",
            "订单簿",
            "回测",
            "因子",
        ),
    )


def _matches_keywords(row: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return False
    tags = row.get("tags") or []
    if isinstance(tags, list):
        tag_text = " ".join(str(tag) for tag in tags)
    else:
        tag_text = str(tags)
    text = " ".join(
        str(row.get(field, ""))
        for field in (
            "title",
            "abstract",
            "raw_text",
            "one_line_summary",
            "technical_summary",
            "quant_relevance",
            "possible_use_case",
        )
    )
    text = f"{text} {tag_text}"
    lower_text = text.lower()
    return any(_keyword_matches(keyword, text, lower_text) for keyword in keywords)


def _keyword_matches(keyword: str, text: str, lower_text: str) -> bool:
    if not keyword:
        return False
    if any("\u3400" <= char <= "\u9fff" for char in keyword):
        return keyword in text
    normalized = keyword.lower().strip()
    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", lower_text))
