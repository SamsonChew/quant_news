from __future__ import annotations

from dataclasses import dataclass
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
        description="只收深度学习在量化中的应用：论文、知乎、X、论坛和博客里关于 Transformer、神经网络、强化学习、深度时间序列建模、订单簿预测等方向的内容。这个频道用于给老板快速判断“未来在哪里”。",
        source_types=("paper", "forum", "blog", "news", "social", "zhihu", "x"),
        keywords=(
            "deep learning",
            "neural",
            "transformer",
            "attention",
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
        key="papers",
        label="论文研究",
        description="来自 arXiv 等论文源的研究内容，适合进入精读或复现队列。",
        source_types=("paper",),
    ),
    ReportSection(
        key="forum_signals",
        label="论坛信号",
        description="来自论坛和社区的实践讨论、争议和经验反馈。",
        source_types=("forum",),
    ),
    ReportSection(
        key="code_tools",
        label="代码与工具",
        description="GitHub 项目、回测框架、数据工具和研究基础设施。",
        source_types=("github",),
    ),
    ReportSection(
        key="alpha_strategy",
        label="策略与因子",
        description="阿尔法、因子、统计套利和可转化为研究任务的策略线索。",
        categories=("Alpha / Factor Research", "Statistical Arbitrage"),
    ),
    ReportSection(
        key="ml_llm",
        label="机器学习 / 大模型量化",
        description="金融机器学习、大模型、智能体和研究自动化相关内容。",
        categories=("Machine Learning for Finance", "LLM / Agents for Quant"),
    ),
    ReportSection(
        key="risk_execution",
        label="风险与执行",
        description="风险管理、交易执行、交易成本、滑点和市场冲击。",
        categories=("Risk Management", "Execution / Transaction Cost"),
    ),
    ReportSection(
        key="microstructure",
        label="市场微观结构",
        description="订单簿、流动性、价差、短周期信号和市场结构。",
        categories=("Market Microstructure",),
    ),
    ReportSection(
        key="portfolio",
        label="组合构建",
        description="组合优化、资产配置、风险预算和再平衡。",
        categories=("Portfolio Construction",),
    ),
    ReportSection(
        key="options_vol",
        label="期权与波动率",
        description="期权、隐含波动率、波动率预测和对冲。",
        categories=("Options / Volatility",),
    ),
    ReportSection(
        key="crypto",
        label="加密资产量化",
        description="加密资产市场结构、链上信号、衍生品和跨交易所机会。",
        categories=("Crypto Quant",),
    ),
    ReportSection(
        key="data_infra",
        label="数据与基础设施",
        description="数据采集、特征流水线、数据质量和研究平台工程。",
        categories=("Data Engineering", "Backtesting / Research Tools"),
    ),
)


def row_section_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    category = str(row.get("category", ""))
    source_type = str(row.get("source_type", ""))
    for section in REPORT_SECTIONS:
        category_match = category in section.categories
        source_type_match = source_type in section.source_types
        keyword_match = _matches_keywords(row, section.keywords)
        if section.require_keyword:
            if keyword_match and (
                category_match
                or source_type_match
                or (not section.categories and not section.source_types)
            ):
                keys.append(section.key)
        elif category_match or source_type_match or keyword_match:
            keys.append(section.key)
    return keys or ["other"]


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
    text = f"{text} {tag_text}".lower()
    return any(keyword.lower() in text for keyword in keywords)
