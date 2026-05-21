from __future__ import annotations

from collections import Counter

from quant_intel.models import Item


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Alpha / Factor Research": [
        "alpha",
        "factor",
        "cross-section",
        "anomaly",
        "signal",
        "predictability",
        "return forecast",
    ],
    "Statistical Arbitrage": [
        "statistical arbitrage",
        "pairs trading",
        "mean reversion",
        "cointegration",
        "spread",
    ],
    "Portfolio Construction": [
        "portfolio",
        "allocation",
        "optimization",
        "risk parity",
        "mean variance",
        "rebalancing",
    ],
    "Risk Management": [
        "risk",
        "var",
        "cvar",
        "drawdown",
        "stress test",
        "hedging",
        "exposure",
    ],
    "Options / Volatility": [
        "option",
        "volatility",
        "implied vol",
        "variance",
        "greeks",
        "derivative",
    ],
    "Market Microstructure": [
        "microstructure",
        "limit order book",
        "order book",
        "liquidity",
        "spread",
        "price impact",
    ],
    "Execution / Transaction Cost": [
        "execution",
        "transaction cost",
        "slippage",
        "market impact",
        "twap",
        "vwap",
        "routing",
    ],
    "Machine Learning for Finance": [
        "machine learning",
        "deep learning",
        "neural",
        "transformer",
        "forecasting",
        "time series",
        "reinforcement learning",
        "attention",
        "foundation model",
        "representation learning",
        "lstm",
        "gnn",
        "深度学习",
        "神经网络",
        "强化学习",
        "时间序列大模型",
        "订单簿预测",
    ],
    "LLM / Agents for Quant": [
        "llm",
        "large language model",
        "agent",
        "rag",
        "prompt",
        "reasoning",
    ],
    "Crypto Quant": [
        "crypto",
        "bitcoin",
        "ethereum",
        "defi",
        "blockchain",
        "perpetual",
    ],
    "Data Engineering": [
        "data pipeline",
        "dataset",
        "etl",
        "feature store",
        "market data",
        "database",
    ],
    "Backtesting / Research Tools": [
        "backtest",
        "backtesting",
        "research tool",
        "framework",
        "library",
        "package",
        "simulator",
    ],
}


def classify_item(item: Item) -> Item:
    title = item.title.lower()
    text = item.readable_text.lower()
    counts: Counter[str] = Counter()
    matched_tags: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                counts[category] += 2
                matched_tags.append(keyword)
            elif keyword in text:
                counts[category] += 1
                matched_tags.append(keyword)

    if counts:
        item.category = counts.most_common(1)[0][0]
    elif item.source_type == "github":
        item.category = "Backtesting / Research Tools"
    elif item.source_type == "paper":
        item.category = "Machine Learning for Finance"
    else:
        item.category = "Alpha / Factor Research"

    item.tags = sorted(set(matched_tags))[:8]
    return item
