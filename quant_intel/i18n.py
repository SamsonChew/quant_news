from __future__ import annotations


CATEGORY_ZH = {
    "Alpha / Factor Research": "阿尔法 / 因子研究",
    "Statistical Arbitrage": "统计套利",
    "Portfolio Construction": "组合构建",
    "Risk Management": "风险管理",
    "Options / Volatility": "期权 / 波动率",
    "Market Microstructure": "市场微观结构",
    "Execution / Transaction Cost": "交易执行 / 交易成本",
    "Machine Learning for Finance": "金融机器学习",
    "LLM / Agents for Quant": "量化大模型 / 智能体",
    "Crypto Quant": "加密资产量化",
    "Data Engineering": "数据工程",
    "Backtesting / Research Tools": "回测 / 研究工具",
    "Industry / Career": "行业 / 职业 / 合规",
    "Unclassified": "未分类",
}


PRIORITY_ZH = {
    "High": "高",
    "Medium": "中",
    "Low": "低",
    "高": "高",
    "中": "中",
    "低": "低",
}


SOURCE_TYPE_ZH = {
    "paper": "论文",
    "forum": "论坛",
    "github": "代码仓库",
    "blog": "博客",
    "news": "新闻",
    "social": "社交媒体",
    "zhihu": "知乎",
    "x": "X",
    "quantml": "QuantML",
}


def category_zh(category: str) -> str:
    return CATEGORY_ZH.get(category, category)


def priority_zh(priority: str) -> str:
    return PRIORITY_ZH.get(priority, priority)


def source_type_zh(source_type: str) -> str:
    return SOURCE_TYPE_ZH.get(source_type, source_type)
