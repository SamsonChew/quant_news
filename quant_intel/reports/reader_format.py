from __future__ import annotations

import re
from typing import Any

from quant_intel.i18n import category_zh, source_type_zh


CJK_RE = re.compile(r"[\u3400-\u9fff]")

TOPIC_ZH = {
    "alpha": "阿尔法",
    "attention": "注意力机制",
    "backtest": "回测",
    "backtesting": "回测",
    "crypto": "加密资产",
    "deep learning": "深度学习",
    "derivative": "衍生品",
    "execution": "交易执行",
    "factor": "因子",
    "forecasting": "预测",
    "limit order book": "订单簿",
    "liquidity": "流动性",
    "market impact": "市场冲击",
    "microstructure": "市场微观结构",
    "momentum": "动量",
    "optimization": "优化",
    "option": "期权",
    "order book": "订单簿",
    "portfolio": "组合",
    "rag": "检索增强生成",
    "reinforcement learning": "强化学习",
    "representation learning": "表征学习",
    "return forecast": "收益预测",
    "risk": "风险",
    "risk parity": "风险平价",
    "slippage": "滑点",
    "spread": "价差",
    "transaction cost": "交易成本",
    "transformer": "Transformer",
    "var": "风险价值",
    "variance": "方差",
    "volatility": "波动率",
}


def with_reader_format(row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    enriched["display_title"] = display_title(row)
    enriched["tldr"] = tldr(row)
    enriched["core_value"] = core_value(row)
    enriched["key_points_list"] = key_points(row)
    enriched["reference_url"] = reference_url(row)
    return enriched


def display_title(row: dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip()
    if _has_cjk(title):
        return title
    category = category_zh(str(row.get("category") or "未分类"))
    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row)
    return f"{category}：{topic}方向{source_type}"


def tldr(row: dict[str, Any]) -> str:
    text = str(row.get("one_line_summary") or "").strip()
    if _has_cjk(text):
        return text

    category = category_zh(str(row.get("category") or "未分类"))
    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row)
    if row.get("source_type") == "paper":
        return f"这是一条关于{category}的论文情报，核心关注{topic}，适合判断是否进入精读、复现或因子研究队列。"
    if row.get("source_type") == "github":
        return f"这是一个关于{category}的代码与工具线索，重点在{topic}，适合评估是否能提升研究、回测或组合构建效率。"
    if row.get("source_type") == "forum":
        return f"这是一条关于{category}的社区讨论，重点在{topic}，适合捕捉实盘经验、争议点和需要验证的假设。"
    if row.get("source_type") in {"social", "zhihu", "x"}:
        return f"这是一条关于{category}的社交媒体信号，重点在{topic}，适合快速判断行业关注方向和潜在研究主题。"
    return f"这是一条关于{category}的{source_type}情报，重点在{topic}，适合纳入每日量化研究观察。"


def core_value(row: dict[str, Any]) -> str:
    relevance = str(row.get("quant_relevance") or "").strip()
    use_case = str(row.get("possible_use_case") or "").strip()
    if relevance and use_case:
        return _zh_cleanup(f"{relevance} 对你的量化工作帮助：{use_case}")
    return _zh_cleanup(
        relevance
        or use_case
        or "需要人工复核后判断是否能转化为研究、回测或生产任务。"
    )


def key_points(row: dict[str, Any], limit: int = 3) -> list[str]:
    points = row.get("key_points") or []
    if isinstance(points, str):
        points = [points]
    clean_points = [str(point).strip() for point in points if str(point).strip()]
    if clean_points and any(_has_cjk(point) for point in clean_points):
        while len(clean_points) < limit:
            clean_points.append("需要打开原文进一步确认方法、数据和适用边界。")
        return clean_points[:limit]

    category = category_zh(str(row.get("category") or "未分类"))
    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row)
    generated_points = [
        f"核心主题：这条{source_type}围绕{category}，重点关注{topic}。",
        f"研究价值：可以先作为{category}方向的候选线索，再决定是否进入精读、复现或小规模回测。",
        f"验证重点：需要检查数据可得性、样本外稳定性、交易成本、可复现性和生产约束。",
    ]
    if row.get("source_type") == "github":
        generated_points[2] = "验证重点：需要检查开源协议、维护活跃度、测试覆盖、API 稳定性和与你资产类别的匹配度。"
    if row.get("source_type") in {"forum", "social", "zhihu", "x"}:
        generated_points[2] = "验证重点：社区和社交媒体观点只能作为线索，必须回到数据、论文或代码验证后再形成研究结论。"
    clean_points = generated_points
    if not clean_points:
        fallback = str(row.get("technical_summary") or row.get("one_line_summary") or "").strip()
        if fallback:
            clean_points = [fallback]
    while len(clean_points) < limit:
        clean_points.append("需要打开原文进一步确认方法、数据和适用边界。")
    return clean_points[:limit]


def reference_url(row: dict[str, Any]) -> str:
    url = str(row.get("url") or "").strip()
    if url.startswith(("https://", "http://")):
        return url
    return ""


def _has_cjk(value: str) -> bool:
    return bool(CJK_RE.search(value))


def _topic_label(row: dict[str, Any]) -> str:
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    labels: list[str] = []
    for tag in tags:
        tag_text = str(tag).strip()
        if not tag_text:
            continue
        mapped = TOPIC_ZH.get(tag_text.lower(), tag_text if _has_cjk(tag_text) else "")
        if mapped and mapped not in labels:
            labels.append(mapped)
        if len(labels) >= 3:
            break
    if labels:
        return "、".join(labels)
    return category_zh(str(row.get("category") or "未分类"))


def _zh_cleanup(value: str) -> str:
    replacements = {
        "代码 Agent": "代码智能体",
        "代码 Agents": "代码智能体",
        "alpha": "阿尔法",
        "Alpha": "阿尔法",
        "Agent": "智能体",
        "Agents": "智能体",
        "crypto": "加密资产",
        "Crypto": "加密资产",
        "benchmark": "基准比较",
        "sandbox": "沙盒环境",
        "API": "接口",
        "license": "开源协议",
    }
    cleaned = value
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = cleaned.replace(" 阿尔法 ", "阿尔法")
    cleaned = cleaned.replace(" 智能体 ", "智能体")
    return cleaned
