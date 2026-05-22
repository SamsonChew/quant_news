from __future__ import annotations

import re
from typing import Any

from quant_intel.i18n import category_zh, source_type_zh
from quant_intel.models import Item, Score, Summary, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, truncate


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


CATEGORY_RELEVANCE = {
    "Alpha / Factor Research": "适合进入阿尔法发现、特征研究或因子有效性验证流程。",
    "Statistical Arbitrage": "和相对价值、价差建模、均值回复策略设计相关。",
    "Portfolio Construction": "和资产配置、组合约束、再平衡以及风险调整优化相关。",
    "Risk Management": "和敞口控制、压力测试、回撤管理以及风险度量相关。",
    "Options / Volatility": "和衍生品研究、波动率预测以及对冲流程相关。",
    "Market Microstructure": "和流动性、订单簿动态、短周期 alpha 以及执行质量相关。",
    "Execution / Transaction Cost": "和滑点控制、市场冲击建模以及生产交易执行相关。",
    "Machine Learning for Finance": "和预测建模、时间序列学习、表征学习以及模型评估相关。",
    "LLM / Agents for Quant": "和研究自动化、文档智能、代码智能体以及量化工作流工具相关。",
    "Crypto Quant": "和加密资产市场结构、链上信号、衍生品以及跨交易所交易相关。",
    "Data Engineering": "和市场数据采集、特征流水线、数据质量以及研究基础设施相关。",
    "Backtesting / Research Tools": "和实验效率、可复现性、仿真质量以及研究基础设施相关。",
    "Industry / Career": "和量化团队招聘、竞业约束、职业路径、合规沟通以及人员流动风险相关。",
}


CATEGORY_USE_CASE = {
    "Alpha / Factor Research": "可以放入研究待办池，作为候选信号或因子族继续验证。",
    "Statistical Arbitrage": "可以作为配对交易、价差交易或相对价值回测的起点。",
    "Portfolio Construction": "可以和当前配置、约束以及风险预算流程做对比测试。",
    "Risk Management": "可以转化为风险检查、敞口报告或压力情景。",
    "Options / Volatility": "可以在波动率曲面、期权收益或对冲后 PnL 序列上测试。",
    "Market Microstructure": "可以用于改进订单簿特征、流动性过滤器或短周期预测。",
    "Execution / Transaction Cost": "可以和当前交易成本、滑点以及市场冲击假设做 benchmark。",
    "Machine Learning for Finance": "可以评估模型设计是否改善预测效果、鲁棒性或特征抽取。",
    "LLM / Agents for Quant": "可以用于改进研究自动化、论文筛选或代码生成工作流。",
    "Crypto Quant": "可以在高流动性交易所上验证，并纳入手续费、资金费率和滑点。",
    "Data Engineering": "可以用于数据采集、校验、血缘追踪或特征生成。",
    "Backtesting / Research Tools": "可以先在沙盒环境里试用，评估接口、复现性和维护风险。",
    "Industry / Career": "可以放入团队管理和合规备忘录，不直接进入策略研究池。",
}


def summarize_item(item: Item, score: Score) -> Summary:
    text = clean_text(item.abstract or item.raw_text or item.title)
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    if not sentences and text:
        sentences = [text]

    one_line = truncate(sentences[0] if sentences else item.title, 220)
    technical = " ".join(sentences[:4]) if sentences else item.title
    technical = truncate(technical, 900)

    key_points = [truncate(sentence, 180) for sentence in sentences[:3]]
    while len(key_points) < 3:
        fallback = {
            0: f"分类：{category_zh(item.category)}。",
            1: f"来源类型：{source_type_zh(item.source_type)}。",
            2: "进入研究或生产前需要进一步人工复核。",
        }[len(key_points)]
        key_points.append(fallback)

    if score.final_score >= 7.5:
        priority = "高"
    elif score.final_score >= 5.5:
        priority = "中"
    else:
        priority = "低"

    limitations = _limitations_for(item)

    return Summary(
        item_id=item.id,
        one_line_summary=one_line,
        technical_summary=technical,
        key_points=key_points,
        quant_relevance=CATEGORY_RELEVANCE.get(
            item.category,
            "如果能连接到可度量的市场行为或研究流程改进，就值得继续跟踪。",
        ),
        possible_use_case=CATEGORY_USE_CASE.get(
            item.category,
            "先加入 watchlist，再判断是否能支持一个具体研究任务。",
        ),
        limitations=limitations,
        read_priority=priority,
        created_at=utc_now_iso(),
    )


def summary_from_llm_payload(
    item: Item,
    score: Score,
    payload: dict[str, Any],
    model_name: str,
) -> Summary:
    fallback = summarize_item(item, score)

    def text_field(key: str, default: str) -> str:
        value = str(payload.get(key, "")).strip()
        return value or default

    key_points = payload.get("key_points")
    if not isinstance(key_points, list):
        key_points = []
    key_points = [str(point).strip() for point in key_points if str(point).strip()][:3]
    while len(key_points) < 3:
        key_points.append(fallback.key_points[len(key_points)])

    priority = str(payload.get("read_priority", fallback.read_priority)).strip()
    if priority not in {"高", "中", "低"}:
        priority = fallback.read_priority

    # Prefer the new title_one_line over old one_line_summary as the display title
    one_line = text_field("title_one_line", "") or text_field("one_line_summary", fallback.one_line_summary)
    # Use core_idea as the richer technical summary if available
    technical = text_field("core_idea", "") or text_field("technical_summary", fallback.technical_summary)
    # quant_impact is a new field; fall back to quant_relevance
    quant_relevance = text_field("quant_impact", "") or text_field("quant_relevance", fallback.quant_relevance)

    return Summary(
        item_id=item.id,
        one_line_summary=truncate(one_line, 300),
        technical_summary=truncate(technical, 1200),
        key_points=[truncate(point, 220) for point in key_points],
        quant_relevance=quant_relevance,
        possible_use_case=text_field("possible_use_case", fallback.possible_use_case),
        limitations=text_field("limitations", fallback.limitations),
        read_priority=priority,
        model_name=model_name,
        created_at=utc_now_iso(),
        key_figures_md=str(payload.get("key_figures_md", "") or ""),
    )


def _limitations_for(item: Item) -> str:
    if item.source_type == "paper":
        return "需要检查数据可得性、交易成本、样本外鲁棒性，以及结果在真实执行假设下是否仍然成立。"
    if item.source_type == "github":
        return "需要检查开源协议、维护活跃度、测试覆盖、接口稳定性，以及示例是否匹配你的资产类别。"
    if item.source_type == "forum":
        if item.category == "Industry / Career":
            return "职业和合规类讨论需要结合司法辖区、合同条款和公司政策核对，不能当作交易或研究结论。"
        return "论坛观点先视为经验性信息，只有经过可复现数据、成本和风控验证后才能进入研究结论。"
    if item.source_type in {"social", "zhihu", "x"}:
        return "社交媒体内容适合捕捉趋势和共识变化，但需要回到论文、代码或数据验证后再形成研究判断。"
    if item.source_type == "blog":
        return "需要独立验证论点，尤其注意幸存者偏差、成本缺失和案例选择偏差。"
    return "在成为研究或交易决策前，需要人工复核。"
