from __future__ import annotations

from collections import Counter
import re

from quant_intel.models import Item


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Alpha / Factor Research": [
        "alpha",
        "阿尔法",
        "factor",
        "因子",
        "momentum",
        "cross-section",
        "anomaly",
        "signal",
        "信号",
        "predictability",
        "return forecast",
        "收益预测",
    ],
    "Statistical Arbitrage": [
        "statistical arbitrage",
        "统计套利",
        "pairs trading",
        "配对交易",
        "mean reversion",
        "均值回复",
        "cointegration",
        "协整",
        "spread",
        "价差",
    ],
    "Portfolio Construction": [
        "portfolio",
        "组合",
        "allocation",
        "配置",
        "optimization",
        "优化",
        "risk parity",
        "风险平价",
        "mean variance",
        "均值方差",
        "rebalancing",
        "再平衡",
    ],
    "Risk Management": [
        "risk",
        "风险",
        "var",
        "cvar",
        "drawdown",
        "回撤",
        "stress test",
        "压力测试",
        "hedging",
        "对冲",
        "exposure",
        "敞口",
    ],
    "Options / Volatility": [
        "option",
        "期权",
        "volatility",
        "波动率",
        "implied vol",
        "隐含波动率",
        "variance",
        "greeks",
        "derivative",
        "derivatives",
        "interest rate",
        "interest-rate",
        "libor",
        "sofr",
        "pricing",
        "fourier-laplace",
        "carr-madan",
        "衍生品",
    ],
    "Market Microstructure": [
        "microstructure",
        "市场微观结构",
        "limit order book",
        "订单簿",
        "order book",
        "liquidity",
        "流动性",
        "spread",
        "价差",
        "price impact",
        "价格冲击",
    ],
    "Execution / Transaction Cost": [
        "execution",
        "交易执行",
        "transaction cost",
        "交易成本",
        "slippage",
        "滑点",
        "market impact",
        "市场冲击",
        "twap",
        "vwap",
        "routing",
    ],
    "Machine Learning for Finance": [
        "machine learning",
        "机器学习",
        "deep learning",
        "neural",
        "transformer",
        "forecasting",
        "time series",
        "reinforcement learning",
        "attention layer",
        "attention layers",
        "self-attention",
        "foundation model",
        "representation learning",
        "feature engineering",
        "fractional differentiation",
        "fractionally differenced",
        "lstm",
        "gnn",
        "diffusion model",
        "graph neural",
        "return prediction",
        "stock prediction",
        "price prediction",
        "financial forecasting",
        "trading agent",
        "portfolio agent",
        "stock trading reinforcement",
        "rl trading",
        "deep rl",
        "强化学习交易",
        "强化学习投资",
        "强化学习组合",
        "深度学习",
        "神经网络",
        "强化学习",
        "时间序列大模型",
        "订单簿预测",
    ],
    "LLM / Agents for Quant": [
        "llm",
        "大模型",
        "large language model",
        "agent",
        "智能体",
        "rag",
        "检索增强生成",
        "prompt",
        "reasoning",
        "chain of thought",
        "chain-of-thought",
        "autoresearch",
        "automated research",
        "alpha generation",
        "factor discovery",
        "hypothesis generation",
        "self-improving",
        "self-reflective",
        "grpo",
        "rlhf",
        "reinforcement learning from human feedback",
        "policy optimization",
        "reward model",
        "ai scientist",
        "自动研究",
        "因子发现",
        "推理模型",
    ],
    "Crypto Quant": [
        "crypto",
        "加密资产",
        "bitcoin",
        "比特币",
        "ethereum",
        "以太坊",
        "defi",
        "blockchain",
        "区块链",
        "perpetual",
        "永续",
    ],
    "Data Engineering": [
        "data pipeline",
        "数据流水线",
        "dataset",
        "数据集",
        "etl",
        "feature store",
        "特征库",
        "market data",
        "市场数据",
        "database",
        "数据库",
        "alt data",
        "alternative data",
        "point-in-time",
        "historical data",
    ],
    "Backtesting / Research Tools": [
        "backtest",
        "回测",
        "backtesting",
        "research tool",
        "研究工具",
        "框架",
        "library",
        "工具包",
        "package",
        "simulator",
        "模拟器",
    ],
    "Industry / Career": [
        "career",
        "hiring",
        "recruit",
        "recruiting",
        "interview",
        "offer in hand",
        "non compete",
        "non-compete",
        "compensation",
        "internship",
        "职业",
        "招聘",
        "面试",
        "竞业",
    ],
}


def classify_item(item: Item) -> Item:
    title = item.title.lower()
    text = item.readable_text.lower()
    counts: Counter[str] = Counter()
    matched_tags: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if _keyword_in_text(keyword, title):
                counts[category] += 2
                matched_tags.append(keyword)
            elif _keyword_in_text(keyword, text):
                counts[category] += 1
                matched_tags.append(keyword)

    if counts:
        item.category = counts.most_common(1)[0][0]
    elif item.source_type == "github":
        item.category = "Backtesting / Research Tools"
    elif item.source_type == "paper":
        item.category = "Machine Learning for Finance"
    elif item.source_type == "forum" and _has_career_context(text):
        item.category = "Industry / Career"
    else:
        item.category = "Alpha / Factor Research"

    item.tags = sorted(set(matched_tags))[:8]
    return item


def _keyword_in_text(keyword: str, text: str) -> bool:
    if not keyword or not text:
        return False

    # CJK terms are intentionally substring matched because word boundaries are
    # not reliable for Chinese text.
    if any("\u3400" <= char <= "\u9fff" for char in keyword):
        return keyword in text

    normalized = keyword.lower().strip()
    if not normalized:
        return False

    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text))


def _has_career_context(text: str) -> bool:
    return any(
        _keyword_in_text(keyword, text)
        for keyword in CATEGORY_KEYWORDS["Industry / Career"]
    )
