from __future__ import annotations

import re
from typing import Any

from quant_intel.i18n import category_zh, source_type_zh


CJK_RE = re.compile(r"[\u3400-\u9fff]")

TOPIC_ZH = {
    "ai": "人工智能",
    "alpha": "阿尔法",
    "algorithm selection": "算法选择",
    "alt data": "另类数据",
    "alternative data": "另类数据",
    "attention": "注意力机制",
    "bayesian": "贝叶斯",
    "backtest": "回测",
    "backtesting": "回测",
    "black-box optimization": "黑箱优化",
    "broker": "券商",
    "brainteaser": "交易面试题",
    "career": "职业发展",
    "cftc": "监管调查",
    "cnn": "卷积神经网络",
    "co-evolutionary": "协同进化",
    "conformal prediction": "保形预测",
    "covariance": "协方差",
    "crypto": "加密资产",
    "data research": "数据研究",
    "data vendor": "数据供应商",
    "decumulation": "养老金领取",
    "deep learning": "深度学习",
    "derivative": "衍生品",
    "diffusion": "扩散模型",
    "drawdown": "回撤",
    "energy": "能源交易",
    "execution": "交易执行",
    "factor": "因子",
    "financial time series": "金融时间序列",
    "forecasting": "预测",
    "fractional differentiation": "分数阶差分",
    "fractionally differenced": "分数阶差分",
    "feature engineering": "特征工程",
    "fourier-laplace": "傅里叶-拉普拉斯方法",
    "free backtesting": "免费回测工具",
    "fourier": "傅里叶方法",
    "graph neural network": "图神经网络",
    "graph neural networks": "图神经网络",
    "high frequency": "高频",
    "hiring": "招聘",
    "indian equities": "印度股票",
    "inference-time optimization": "推理期优化",
    "interview": "面试",
    "interest-rate": "利率衍生品",
    "jump-diffusion": "跳扩散",
    "knowledge graph": "知识图谱",
    "leverage": "杠杆",
    "limit order book": "订单簿",
    "liquidity": "流动性",
    "llm": "大模型",
    "libor": "LIBOR",
    "machine learning": "机器学习",
    "market data": "市场数据",
    "market impact": "市场冲击",
    "mean field games": "平均场博弈",
    "microstructure": "市场微观结构",
    "momentum": "动量",
    "monetary": "货币条件",
    "monthly rotations": "月度轮动",
    "multi-agent": "多智能体",
    "non compete": "竞业协议",
    "non-compete": "竞业协议",
    "optimal allocation": "最优配置",
    "optimal control": "最优控制",
    "optimization": "优化",
    "oracle": "预言机",
    "oil trades": "原油交易",
    "option": "期权",
    "options": "期权",
    "order book": "订单簿",
    "particle filter": "粒子滤波",
    "partial information": "部分信息",
    "offer in hand": "手中 offer",
    "paid non compete": "带薪竞业协议",
    "pension": "养老金",
    "portfolio": "组合",
    "portfolio construction": "组合构建",
    "portfolio optimization": "组合优化",
    "power trading": "电力交易",
    "pricing": "定价",
    "property-based testing": "性质测试",
    "quantum": "量子",
    "quantum annealer": "量子退火",
    "rag": "检索增强生成",
    "reinforcement learning": "强化学习",
    "recruit": "招聘",
    "recruiting": "招聘",
    "regret": "后悔值",
    "regulatory": "监管",
    "regulatory probe": "监管调查",
    "representation learning": "表征学习",
    "resilience": "韧性",
    "resource optimization": "资源优化",
    "return forecasting": "收益预测",
    "return forecast": "收益预测",
    "risk": "风险",
    "risk parity": "风险平价",
    "rl": "强化学习",
    "sequence-adaptive": "序列自适应",
    "slm": "小语言模型",
    "slippage": "滑点",
    "sofr": "SOFR",
    "spread": "价差",
    "stochastic optimization": "随机优化",
    "structured data": "结构化数据",
    "suspicious oil trades": "可疑原油交易",
    "surrogate": "代理模型",
    "testing": "测试",
    "time series": "时间序列",
    "trading agents": "交易智能体",
    "trading brainteaser": "交易面试题",
    "transaction cost": "交易成本",
    "transformer": "Transformer",
    "var": "风险价值",
    "variance": "方差",
    "volatility": "波动率",
}

TITLE_PHRASES = {
    "a momentum strategy using leverage and monthly rotations": "使用杠杆和月度轮动的动量策略",
    "any genuinely free backtesting tools": "真正免费的回测工具有哪些",
    "are fourier-laplace techniques popular in industry for pricing": "傅里叶-拉普拉斯方法在业内定价中是否常用",
    "beyond numerical features": "超越数值特征",
    "built a drawdown monitor across portfolios": "跨组合回撤监控工具",
    "classification of single and mixed partial discharges": "单一与混合局部放电分类",
    "do better volatility forecasts lead to better portfolios": "更好的波动率预测是否带来更好的组合",
    "does swapping the libor rate with the sofr rate really change anything for models": "把 LIBOR 换成 SOFR 会怎样影响模型",
    "energyagentbench": "能源智能体基准",
    "external demand domestic monetary conditions and remittance dynamics": "外部需求、国内货币条件与汇款动态",
    "feature engineering model hacking": "特征工程比调模型更重要",
    "flurry of suspicious oil trades": "可疑原油交易引发监管调查",
    "general-purpose co-evolutionary construction": "通用协同进化构建方法",
    "graph-grounded optimization": "基于知识图谱的优化",
    "help needed on a seemingly easy trading brainteaser": "一道看似简单的交易面试题",
    "indefinite stochastic lq optimal control": "不定随机线性二次最优控制",
    "is the medium-term alpha decay in indian equities a data problem or a structural one": "印度股票中期阿尔法衰减是数据问题还是结构问题",
    "ken griffin shocked depressed at ai's impact on society": "Ken Griffin 谈人工智能对社会的冲击",
    "modern portfolio theory in the crypto-wilderness": "加密资产荒野中的现代组合理论",
    "modeling and resource optimization": "建模与资源优化",
    "non-compete leave without offer in hand": "竞业协议下是否应无 offer 离职",
    "non compete leave without offer in hand": "竞业协议下是否应无 offer 离职",
    "numerical methods for optimal decumulation": "养老金最优领取的数值方法",
    "on the expected maximum deficit": "预期最大赤字与储备最优配置",
    "on the optimal portfolio problem": "部分信息下的最优组合问题",
    "plan before you trade": "交易前先规划",
    "power energy trading": "电力与能源交易",
    "practical ways to estimate slippage": "估计滑点的实用方法",
    "regret equals covariance": "后悔值等于协方差",
    "securing the flow": "保障能源流动安全",
    "structured point-in-time historical data": "时点一致历史数据",
    "the statistical significance of the inclusion of graph neural networks": "图神经网络用于金融时间序列预测的统计显著性",
    "transformer-based intraday return forecasting": "基于 Transformer 的日内收益预测",
    "uncertainty-aware machine learning": "不确定性感知机器学习",
    "us tech 100 data": "美国科技 100 指数数据",
    "weekly megathread": "每周综合讨论",
    "where the quantum lives": "量子优化在混合组合优化中的位置",
    "why factor decay accelerates after public release": "为什么因子公开后衰减会加速",
}

SENTENCE_PHRASES = {
    "a discussion about": "讨论",
    "a python toolkit for": "一个用于",
    "a thread arguing that": "讨论认为",
    "alpha decay": "阿尔法衰减",
    "attention layers": "注意力层",
    "backtesting": "回测",
    "bid-ask spread": "买卖价差",
    "compares": "对比",
    "data vendor availability": "数据供应商普及",
    "deep reinforcement learning": "深度强化学习",
    "directional accuracy": "方向预测准确率",
    "driven by": "来自",
    "experiment tracking": "实验追踪",
    "fractional differentiation consists in transforming non-stationary features like prices into stationary features while preserving some memory": "分数阶差分把价格这类非平稳特征转成更平稳的特征，同时保留一部分历史记忆",
    "fractionally differenced features": "分数阶差分特征",
    "faster replication cycles": "更快的复制周期",
    "for high-frequency return forecasting": "用于高频收益预测",
    "high-frequency return forecasting": "高频收益预测",
    "i recently learned about": "最近在看",
    "intraday futures strategies": "日内期货策略",
    "limit order book states": "订单簿状态",
    "liquidity features": "流动性特征",
    "marcos lopez de prado": "Lopez de Prado",
    "market impact": "市场冲击",
    "mean-variance optimization": "均值方差优化",
    "portfolio optimization": "组合优化",
    "recurrent and linear baselines": "循环模型和线性基线",
    "representation learning": "表征学习",
    "results suggest": "结果显示",
    "really makes a difference": "确实有明显影响",
    "risk budgeting": "风险预算",
    "risk parity": "风险平价",
    "short-horizon labels": "短周期标签",
    "stationary features": "平稳特征",
    "strategy i'm exploring": "正在研究的策略",
    "studies": "研究",
    "the article argues that": "文章认为",
    "the method": "方法",
    "this paper": "这篇论文",
    "transaction cost assumptions": "交易成本假设",
    "transformer models": "Transformer 模型",
    "non-stationary features": "非平稳特征",
    "preserving some memory": "保留部分记忆性",
    "helps ml models generalize better": "帮助机器学习模型更好泛化",
    "walk-forward validation": "滚动样本外验证",
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

    translated = _translate_title(title)
    if translated:
        return translated

    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row, limit=4)
    if row.get("source_type") == "github":
        return f"{topic}工具与代码库"
    if row.get("source_type") == "quantml":
        return f"{topic}QuantML 研究图谱"
    if row.get("source_type") == "forum":
        return f"{topic}实践讨论"
    if row.get("source_type") == "paper":
        return f"{topic}研究论文"
    return f"{topic}{source_type}情报"


def tldr(row: dict[str, Any]) -> str:
    text = str(row.get("one_line_summary") or "").strip()
    if text and not _looks_generic(text):
        return text

    category = category_zh(str(row.get("category") or "未分类"))
    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row, limit=4)
    if _is_libor_sofr_topic(topic):
        return (
            f"这条社区讨论聚焦{topic}：核心问题是从 LIBOR 切到 SOFR 后，利率衍生品模型的曲线构建、"
            "校准输入和历史回测是否需要同步调整。"
        )
    if _is_fractional_diff_topic(topic):
        return (
            "这条社区讨论聚焦特征工程和分数阶差分：用 Lopez de Prado 的分数阶差分把价格特征处理得更平稳，"
            "同时保留一部分历史记忆，用来改善微观结构或机器学习策略的泛化。"
        )
    if "交易面试题" in topic:
        return (
            "这道交易题本质是一个执行节奏问题：月底前买入固定数量，并尝试跑赢最后 5 个交易日均价基准；"
            "重点在基准定义、信息可得性和成交约束。"
        )
    if _is_career_topic(topic):
        return (
            f"这条社区讨论聚焦{topic}，属于职业 / 合规信息；它不提供交易信号，但能帮助判断招聘、"
            "竞业约束、离职窗口和团队执行风险。"
        )
    translated_sentence = _best_translated_sentence(row)
    if translated_sentence:
        if row.get("source_type") == "paper":
            return f"这篇论文聚焦{topic}：{translated_sentence}"
        if row.get("source_type") == "github":
            return f"这个代码库聚焦{topic}：{translated_sentence}"
        if row.get("source_type") == "quantml":
            return f"这条 QuantML 图谱线索聚焦{topic}：{translated_sentence}"
        if row.get("source_type") == "forum":
            return f"这条社区讨论聚焦{topic}：{translated_sentence}"
        if row.get("source_type") in {"social", "zhihu", "x"}:
            return f"这条趋势信号聚焦{topic}：{translated_sentence}"
        return f"这条{source_type}情报聚焦{topic}：{translated_sentence}"

    if row.get("source_type") == "paper":
        return f"这篇论文围绕{topic}展开，属于{category}方向，适合判断是否进入精读、复现或研究待办。"
    if row.get("source_type") == "github":
        return f"这个代码库围绕{topic}提供工具线索，适合评估是否能提升研究、回测或生产工程效率。"
    if row.get("source_type") == "quantml":
        return f"这条 QuantML 图谱线索围绕{topic}展开，适合从金融 AI 文献图谱里发现可验证的 alpha 假设。"
    if row.get("source_type") == "forum":
        return f"这条社区讨论围绕{topic}展开，适合捕捉实盘经验、争议点和需要验证的假设。"
    if row.get("source_type") in {"social", "zhihu", "x"}:
        return f"这条社交媒体信号围绕{topic}展开，适合快速判断行业关注方向和潜在研究主题。"
    return f"这条{source_type}情报围绕{topic}展开，适合纳入每日量化研究观察。"


def core_value(row: dict[str, Any]) -> str:
    category = category_zh(str(row.get("category") or "未分类"))
    topic = _topic_label(row, limit=4)
    source_type = str(row.get("source_type") or "")
    if _is_libor_sofr_topic(topic):
        value = (
            "对你的量化工作帮助：用它检查利率模型迁移风险，尤其是贴现曲线、远期曲线、历史数据拼接、"
            "校准目标和旧回测结果是否因为 LIBOR/SOFR 切换而不可比。"
        )
    elif _is_fractional_diff_topic(topic):
        value = (
            "对你的量化工作帮助：把它转成一个特征工程实验，对比原始价格特征、差分特征和分数阶差分特征，"
            "重点看平稳性、信息保留、样本外泛化和是否引入未来函数。"
        )
    elif "交易面试题" in topic:
        value = (
            "对你的量化工作帮助：把它当作交易直觉和概率推理训练题，适合沉淀成面试题库或研究员基本功检查，"
            "但不能直接转成策略。"
        )
    elif any(marker in topic for marker in ("竞业协议", "职业发展", "招聘", "面试")):
        value = (
            f"对你的量化工作帮助：这不是策略信号，而是{topic}风险提示；适合给团队招聘、跳槽窗口、"
            "竞业约束和合规沟通做检查清单，避免研究人员流动带来的执行风险。"
        )
    elif any(marker in topic for marker in ("监管", "可疑交易", "原油交易", "CFTC")):
        value = (
            f"对你的量化工作帮助：把它当作{topic}案例，用来补充异常交易监控、市场操纵风险、"
            "大宗商品执行和合规审计的场景库。"
        )
    elif source_type == "paper":
        value = (
            f"对你的量化工作帮助：把它拆成一个{category}复现任务，先验证{topic}是否真的带来样本外提升，"
            "再检查交易成本、数据泄漏和换手约束。"
        )
    elif source_type == "github":
        value = (
            f"对你的量化工作帮助：把它当作{topic}相关工具候选，比较接口、数据输入输出、测试覆盖和维护活跃度，"
            "判断能否接入研究流水线。"
        )
    elif source_type == "quantml":
        value = (
            f"对你的量化工作帮助：把它当作{topic}研究图谱入口，用来从论文、模型、任务和市场问题之间找到可复现的研究路径。"
        )
    elif source_type == "forum":
        value = (
            f"对你的量化工作帮助：把它当作{topic}的实盘经验线索，用来补充回测假设、交易成本假设或风控检查清单。"
        )
    elif source_type in {"social", "zhihu", "x"}:
        value = (
            f"对你的量化工作帮助：把它当作{topic}趋势信号，判断团队是否需要提前布局数据、模型或复现实验。"
        )
    elif source_type == "blog":
        value = (
            f"对你的量化工作帮助：把它当作{topic}研究备忘录，用来形成可验证假设，而不是直接当作交易结论。"
        )
    else:
        value = (
            f"对你的量化工作帮助：围绕{topic}补充研究素材，进一步判断是否能转化成因子、回测、风控或工程任务。"
        )
    return _zh_cleanup(value)


def key_points(row: dict[str, Any], limit: int = 3) -> list[str]:
    points = row.get("key_points") or []
    if isinstance(points, str):
        points = [points]
    clean_points = [str(point).strip() for point in points if str(point).strip()]
    if clean_points and not _points_are_generic(clean_points):
        cleaned = [_zh_cleanup(point) for point in clean_points]
        while len(cleaned) < limit:
            cleaned.append(_validation_point(row))
        return cleaned[:limit]

    category = category_zh(str(row.get("category") or "未分类"))
    source_type = source_type_zh(str(row.get("source_type") or "内容"))
    topic = _topic_label(row, limit=4)
    special_points = _special_key_points(topic)
    if special_points:
        return [_zh_cleanup(point) for point in special_points[:limit]]
    translated_sentences = _translated_sentences(row, limit=2)
    generated_points = []
    if translated_sentences:
        generated_points.append(f"内容抓手：{translated_sentences[0]}")
    else:
        generated_points.append(f"内容抓手：这条{source_type}围绕{topic}展开，归入{category}。")
    if len(translated_sentences) > 1:
        generated_points.append(f"方法或证据：{translated_sentences[1]}")
    else:
        generated_points.append(_research_action_point(row, topic, category))
    generated_points.append(_validation_point(row))
    if row.get("source_type") == "github":
        generated_points[2] = "验证重点：检查开源协议、维护活跃度、测试覆盖、接口稳定性和与你资产类别的匹配度。"
    if (
        row.get("source_type") in {"forum", "social", "zhihu", "x"}
        and not _is_career_topic(topic)
        and not _is_libor_sofr_topic(topic)
        and not _is_fractional_diff_topic(topic)
        and "交易面试题" not in topic
    ):
        generated_points[2] = "验证重点：社区和社交媒体观点只能作为线索，必须回到数据、论文或代码验证后再形成研究结论。"
    clean_points = [_zh_cleanup(point) for point in generated_points]
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


def _topic_label(row: dict[str, Any], limit: int = 3) -> str:
    text = " ".join(
        str(row.get(field) or "")
        for field in ("title", "abstract", "raw_text", "one_line_summary", "technical_summary")
    )
    lower_text = text.lower()
    career_context = any(
        _phrase_matches_text(phrase, text, lower_text)
        for phrase in (
            "non compete",
            "non-compete",
            "offer in hand",
            "recruit",
            "recruiting",
            "interview",
            "hiring",
            "career",
        )
    )
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    labels: list[str] = []
    for tag in tags:
        tag_text = str(tag).strip()
        if not tag_text:
            continue
        if not _phrase_matches_text(tag_text, text, lower_text):
            continue
        mapped = TOPIC_ZH.get(tag_text.lower(), tag_text if _has_cjk(tag_text) else "")
        if mapped and _topic_label_allowed(mapped, career_context) and mapped not in labels:
            labels.append(mapped)
        if len(labels) >= limit:
            break
    if len(labels) < limit:
        for phrase, label in sorted(TOPIC_ZH.items(), key=lambda item: len(item[0]), reverse=True):
            if (
                _phrase_matches_text(phrase, text, lower_text)
                and _topic_label_allowed(label, career_context)
                and label not in labels
            ):
                labels.append(label)
            if len(labels) >= limit:
                break
    if labels:
        if "带薪竞业协议" in labels and "竞业协议" in labels:
            labels = [label for label in labels if label != "竞业协议"]
        return "、".join(labels[:limit])
    return category_zh(str(row.get("category") or "未分类"))


def _translate_title(title: str) -> str:
    cleaned = _normalize_for_match(title)
    for phrase, translated in sorted(TITLE_PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in cleaned:
            return translated

    translated = _phrase_translate(title, TITLE_PHRASES | TOPIC_ZH)
    translated = _strip_english_fillers(translated)
    if _chinese_ratio(translated) >= 0.45:
        return _limit(_zh_cleanup(translated), 34)
    return ""


def _best_translated_sentence(row: dict[str, Any]) -> str:
    sentences = _translated_sentences(row, limit=1)
    return sentences[0] if sentences else ""


def _translated_sentences(row: dict[str, Any], limit: int = 2) -> list[str]:
    text = str(row.get("abstract") or row.get("raw_text") or row.get("technical_summary") or row.get("one_line_summary") or "")
    sentences = _split_sentences(text)
    translated: list[str] = []
    for sentence in sentences:
        zh = _translate_sentence(sentence)
        if zh and zh not in translated:
            translated.append(zh)
        if len(translated) >= limit:
            break
    return translated


def _translate_sentence(sentence: str) -> str:
    sentence = sentence.strip()
    if not sentence:
        return ""
    if _has_cjk(sentence):
        return _limit(_zh_cleanup(sentence), 150)

    translated = _phrase_translate(sentence, SENTENCE_PHRASES | TITLE_PHRASES | TOPIC_ZH)
    translated = _strip_english_fillers(translated)
    translated = re.sub(r"\s+", " ", translated).strip(" ,.;:-")
    if _chinese_ratio(translated) < 0.35:
        return ""
    return _limit(_zh_cleanup(translated), 150)


def _phrase_translate(value: str, mapping: dict[str, str]) -> str:
    output = value
    for phrase, translated in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        output = pattern.sub(translated, output)
    output = re.sub(r"\busing\b", "使用", output, flags=re.IGNORECASE)
    output = re.sub(r"\bwith\b", "结合", output, flags=re.IGNORECASE)
    output = re.sub(r"\bvia\b", "通过", output, flags=re.IGNORECASE)
    output = re.sub(r"\bfor\b", "用于", output, flags=re.IGNORECASE)
    output = re.sub(r"\band\b", "和", output, flags=re.IGNORECASE)
    output = re.sub(r"\bor\b", "或", output, flags=re.IGNORECASE)
    output = output.replace("&", "和")
    return output


def _phrase_matches_text(phrase: str, text: str, lower_text: str | None = None) -> bool:
    phrase = phrase.strip()
    if not phrase or not text:
        return False
    if _has_cjk(phrase):
        return phrase in text
    haystack = lower_text if lower_text is not None else text.lower()
    normalized = phrase.lower()
    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack))


def _topic_label_allowed(label: str, career_context: bool) -> bool:
    if not career_context:
        return True
    career_labels = {
        "带薪竞业协议",
        "竞业协议",
        "手中 offer",
        "职业发展",
        "招聘",
        "面试",
        "电力交易",
        "能源交易",
    }
    return label in career_labels


def _is_career_topic(topic: str) -> bool:
    return any(marker in topic for marker in ("竞业协议", "职业发展", "招聘", "手中 offer"))


def _is_libor_sofr_topic(topic: str) -> bool:
    return "LIBOR" in topic or "SOFR" in topic


def _is_fractional_diff_topic(topic: str) -> bool:
    return "分数阶差分" in topic or "特征工程" in topic


def _special_key_points(topic: str) -> list[str]:
    if _is_libor_sofr_topic(topic):
        return [
            "内容抓手：LIBOR 到 SOFR 不是简单替换变量名，会影响利率曲线构建、贴现口径和模型校准。",
            "研究动作：列出旧模型依赖的曲线、历史数据和估值假设，做一张 LIBOR/SOFR 迁移差异表。",
            "验证重点：检查历史回测连续性、校准目标、估值口径和合约 fallback 条款。",
        ]
    if _is_fractional_diff_topic(topic):
        return [
            "内容抓手：分数阶差分试图让价格特征更平稳，同时保留一部分长期记忆，适合做特征工程消融实验。",
            "研究动作：比较原始价格、普通差分和分数阶差分特征在样本外预测、换手和成本后的表现。",
            "验证重点：确认平稳性提升不是未来数据泄漏，并检查参数选择对结果是否过度敏感。",
        ]
    if "交易面试题" in topic:
        return [
            "内容抓手：题目是月底前买入固定数量，并尝试跑赢最后 5 个交易日均价基准。",
            "研究动作：先手算可用信息下的执行节奏，再用小模拟检验买入时点、成交约束和成本敏感性。",
            "验证重点：明确基准窗口、信息可得性、成交成本和成交量约束，否则结论会失真。",
        ]
    if _is_career_topic(topic):
        return [
            f"内容抓手：{topic}属于团队、职业和合规信息，不应直接放进策略研究池。",
            "研究动作：把它转成招聘节奏、离职窗口、竞业约束和合规沟通检查清单。",
            "验证重点：核对法律辖区、合同条款、公司政策和时间窗口。",
        ]
    return []


def _strip_english_fillers(value: str) -> str:
    output = value
    filler_patterns = [
        r"\bthe\b",
        r"\ba\b",
        r"\ban\b",
        r"\bof\b",
        r"\bto\b",
        r"\bin\b",
        r"\bon\b",
        r"\bby\b",
        r"\bfrom\b",
        r"\bis\b",
        r"\bare\b",
        r"\bbe\b",
        r"\bthis\b",
        r"\bthat\b",
    ]
    for pattern in filler_patterns:
        output = re.sub(pattern, " ", output, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", output).strip()


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if _has_cjk(text):
        parts = re.split(r"(?<=[。！？])\s*", text)
    else:
        parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()][:5]


def _research_action_point(row: dict[str, Any], topic: str, category: str) -> str:
    source_type = str(row.get("source_type") or "")
    if _is_libor_sofr_topic(topic):
        return "研究动作：列出 LIBOR 版和 SOFR 版曲线输入、贴现口径、校准目标和历史回测窗口，做一次迁移差异表。"
    if _is_fractional_diff_topic(topic):
        return "研究动作：做一组特征消融实验，比较原始价格、普通差分和分数阶差分在样本外预测上的稳定性。"
    if "交易面试题" in topic:
        return "研究动作：先手算最优执行逻辑，再写一个小模拟验证买入节奏、基准定义和成本敏感性。"
    if _is_career_topic(topic):
        return f"研究动作：不要把{topic}当作交易信号；把它归入团队、合规或职业风险备忘录。"
    if any(marker in topic for marker in ("监管", "可疑交易", "原油交易")):
        return f"研究动作：把{topic}转成异常交易案例，检查是否能启发监控指标或风控阈值。"
    if source_type == "paper":
        return f"研究动作：把{topic}拆成复现计划，明确数据、标签、基线模型和交易成本假设。"
    if source_type == "github":
        return f"研究动作：用小样本数据试跑{topic}相关功能，比较接口复杂度、运行速度和结果可解释性。"
    if source_type == "quantml":
        return f"研究动作：从 QuantML 图谱里追踪{topic}相关论文、模型和任务，挑一条能复现的路径进入研究待办。"
    if source_type == "forum":
        return f"研究动作：把讨论里的{topic}观点转成可回测假设，避免只吸收社区结论。"
    if source_type in {"social", "zhihu", "x"}:
        return f"研究动作：把{topic}作为趋势观察项，继续跟踪论文、代码和数据源是否同步出现。"
    return f"研究动作：先作为{category}候选线索，判断是否值得进入研究待办。"


def _validation_point(row: dict[str, Any]) -> str:
    source_type = str(row.get("source_type") or "")
    topic = _topic_label(row, limit=4)
    if _is_libor_sofr_topic(topic):
        return "验证重点：核对利率定义、曲线构建、历史数据连续性、模型校准和估值口径，不要只做变量名替换。"
    if _is_fractional_diff_topic(topic):
        return "验证重点：检查平稳性提升是否来自未来数据泄漏，并比较样本外收益、换手、成本和特征稳定性。"
    if "交易面试题" in topic:
        return "验证重点：题目默认条件通常很强，要显式检查成交成本、成交量约束、基准窗口和信息可得性。"
    if _is_career_topic(topic):
        return "验证重点：这类内容优先核对法律辖区、合同条款、公司政策和时间窗口，不应进入策略研究结论。"
    if any(marker in topic for marker in ("监管", "可疑交易", "原油交易")):
        return "验证重点：核对原始报道、监管主体、涉事市场和时间线，避免把新闻噪音误判成可交易信号。"
    if source_type == "paper":
        return "验证重点：检查样本外表现、交易成本、数据泄漏、基线选择和真实执行约束。"
    if source_type == "github":
        return "验证重点：检查开源协议、维护活跃度、测试覆盖、接口稳定性和生产依赖风险。"
    if source_type == "quantml":
        return "验证重点：回到原始论文、代码和数据，确认图谱线索是否有可复现证据和清晰市场假设。"
    if source_type == "forum":
        return "验证重点：论坛观点必须回到可复现数据、成本和风控约束，不能直接变成研究结论。"
    if source_type in {"social", "zhihu", "x"}:
        return "验证重点：社交媒体只代表趋势信号，需要用论文、代码或数据交叉验证。"
    return "验证重点：检查数据可得性、可复现性、样本外稳定性和生产约束。"


def _points_are_generic(points: list[str]) -> bool:
    generic_markers = (
        "来源类型",
        "进入研究或生产前",
        "需要进一步人工复核",
        "分类：",
    )
    return any(any(marker in point for marker in generic_markers) for point in points)


def _looks_generic(value: str) -> bool:
    markers = (
        "这是一条关于",
        "适合判断是否进入",
        "适合纳入每日量化研究观察",
        "方向的候选线索",
    )
    return any(marker in value for marker in markers)


def _normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _chinese_ratio(value: str) -> float:
    if not value:
        return 0.0
    cjk_count = len(CJK_RE.findall(value))
    latin_count = len(re.findall(r"[A-Za-z]", value))
    return cjk_count / max(cjk_count + latin_count, 1)


def _limit(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


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
    for token in ("Transformer", "LIBOR", "SOFR", "Python", "CFTC"):
        cleaned = re.sub(rf"(?<=[\u3400-\u9fff]){re.escape(token)}", f" {token}", cleaned)
        cleaned = re.sub(rf"{re.escape(token)}(?=[\u3400-\u9fff])", f"{token} ", cleaned)
    cleaned = cleaned.replace(" 阿尔法 ", "阿尔法")
    cleaned = cleaned.replace(" 智能体 ", "智能体")
    cleaned = cleaned.replace("工具包相关工具候选", "工具候选")
    cleaned = cleaned.replace("工具包工具候选", "工具候选")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()
