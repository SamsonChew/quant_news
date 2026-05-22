from __future__ import annotations

from datetime import date

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import stable_hash
from quant_intel.sources.base import Source


class SampleSource(Source):
    name = "Sample"

    def fetch(self) -> list[Item]:
        today = date.today().isoformat()
        samples = [
            {
                "source": "arXiv",
                "source_type": "paper",
                "title": "基于 Transformer 和订单簿特征的日内收益预测",
                "url": "https://arxiv.org/abs/2605.17724v1",
                "abstract": "这篇论文研究如何用订单簿状态、流动性特征和短周期标签训练 Transformer 模型预测高频收益。方法对比注意力层、循环模型和线性基线，并加入交易成本假设。结果显示方向预测可能改善，但收益边际对手续费和市场冲击非常敏感。",
            },
            {
                "source": "GitHub",
                "source_type": "github",
                "title": "开源组合研究实验室",
                "url": "https://github.com/microsoft/qlib",
                "abstract": "一个用于组合优化、风险预算、回测和实验追踪的 Python 工具包，包含均值方差优化、风险平价和滚动样本外验证示例。",
                "metadata": {"stars": 482, "forks": 48, "language": "Python"},
            },
            {
                "source": "Reddit algotrading",
                "source_type": "forum",
                "title": "小型期货策略如何估计滑点",
                "url": "https://www.reddit.com/r/algotrading/",
                "abstract": "这条讨论聚焦日内期货策略的滑点估计，包括采样买卖价差、限制成交量参与率，以及对比模拟成交和实盘成交差异。",
                "metadata": {"comments": 36},
            },
            {
                "source": "Quant Blog",
                "source_type": "blog",
                "title": "为什么因子公开后衰减会加速",
                "url": "https://www.quantstart.com/articles/",
                "abstract": "文章认为阿尔法衰减主要来自拥挤交易、数据供应商普及和更快的复制周期，并建议监控换手率、融券约束以及与热门因子的相关性。",
            },
            {
                "source": "知乎",
                "source_type": "zhihu",
                "title": "深度学习正在改变量化研究范式：从特征工程到端到端表征学习",
                "url": "https://www.zhihu.com/topic/19559450/hot",
                "abstract": "讨论 Transformer、深度时间序列模型和表征学习如何减少传统因子工程依赖，并在订单簿预测、组合构建和风险建模中形成新的研究范式。",
                "metadata": {"comments": 18},
            },
            {
                "source": "X",
                "source_type": "x",
                "title": "订单簿深度学习预测正在成为生产级研究方向",
                "url": "https://x.com/search?q=limit%20order%20book%20deep%20learning%20quant&src=typed_query",
                "abstract": "这条讨论认为，基于 Transformer 的订单簿模型、表征学习和用于交易执行的深度强化学习，正在从论文走向生产级量化研究。",
                "metadata": {"likes": 420, "reposts": 76},
            },
        ]

        items: list[Item] = []
        for sample in samples:
            title = sample["title"]
            abstract = sample["abstract"]
            source = sample["source"]
            items.append(
                Item(
                    id=stable_hash([source, title]),
                    source=source,
                    source_type=sample["source_type"],
                    title=title,
                    url=sample.get("url", ""),
                    published_at=today,
                    collected_at=utc_now_iso(),
                    raw_text=abstract,
                    abstract=abstract,
                    content_hash=stable_hash([title, abstract]),
                    metadata=sample.get("metadata", {}),
                )
            )
        return items
