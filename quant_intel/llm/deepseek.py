from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quant_intel.i18n import source_type_zh
from quant_intel.models import Item, Score
from quant_intel.pipeline.normalize import truncate

PROMPT_VERSION = "v2"

_INSTRUCTIONS_PATH = Path(__file__).resolve().parents[2] / "prompts" / "summary_instructions.md"

_INSTRUCTIONS_CACHE: str | None = None


def _load_instructions() -> str:
    global _INSTRUCTIONS_CACHE
    if _INSTRUCTIONS_CACHE is None:
        if _INSTRUCTIONS_PATH.exists():
            _INSTRUCTIONS_CACHE = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
        else:
            _INSTRUCTIONS_CACHE = "你是资深量化研究员，只处理和量化、AI、大模型相关内容，输出 JSON。"
    return _INSTRUCTIONS_CACHE


@dataclass(frozen=True, slots=True)
class DeepSeekConfig:
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/chat/completions"
    timeout_seconds: int = 45
    max_input_chars: int = 6000


class DeepSeekClient:
    def __init__(self, config: DeepSeekConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "DeepSeekClient | None":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        base_url = (
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
            .strip()
            or "https://api.deepseek.com/chat/completions"
        )
        return cls(DeepSeekConfig(api_key=api_key, model=model, base_url=base_url))

    def summarize(self, item: Item, score: Score) -> dict[str, Any]:
        """Returns parsed summary payload, or {"skip": True} if content is not relevant."""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": _load_instructions()},
                {"role": "user", "content": self._prompt(item, score)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {body[:240]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)

        if parsed.get("skip"):
            return {"skip": True}

        return _validate_summary_payload(parsed, item)

    def generate_alpha_ideas(self, rows: list[dict[str, Any]], n: int = 3) -> str:
        """Generate n alpha ideas from X/forum posts using deepseek-reasoner."""
        if not rows:
            return ""

        x_forum_rows = [
            r for r in rows
            if str(r.get("source_type", "")).lower() in ("x", "forum", "social", "zhihu")
        ]
        candidates = x_forum_rows if len(x_forum_rows) >= 3 else rows

        items_text = "\n\n".join(
            f"### {row.get('title', '')}\n"
            f"来源：{row.get('source', '')} | 来源类型：{row.get('source_type', '')} | 分类：{row.get('category', '')}\n"
            f"摘要：{row.get('one_line_summary') or row.get('abstract') or row.get('raw_text', '')[:400]}"
            for row in candidates[:10]
        )

        prompt = f"""今天从 X / 论坛收集到的量化相关讨论如下：

{items_text}

---

请从上面的内容中提炼 {n} 个最有意思的 alpha ideas。每个 idea 只需简短描述核心概念，不需要完整拆解。

输出格式（严格 JSON）：
{{
  "ideas": [
    {{
      "alpha_name": "idea 的简短名字（不超过 20 字）",
      "idea_type": "idea 的类型，例如：动量因子、情绪信号、订单流策略、套利机会等",
      "source_item": "来自哪篇帖子 / 推文（标题或账号）",
      "core_insight": "这个 alpha 的核心洞察是什么，2-3 句话，说清楚为什么 market 会有这个机会"
    }}
  ]
}}

只输出 JSON，全部中文，ideas 列表恰好 {n} 条。"""

        reasoner_model = (
            os.environ.get("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner").strip()
            or "deepseek-reasoner"
        )
        payload = {
            "model": reasoner_model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是资深量化研究员，从论坛和社交媒体讨论中提炼可执行的 alpha 想法。只输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            result = _extract_json(content)
            ideas = result.get("ideas", [])
            return _render_alpha_ideas(ideas, model_name=reasoner_model)
        except Exception as exc:
            return f"> Alpha ideas 生成失败：{exc}"

    def generate_alpha_idea(self, rows: list[dict[str, Any]]) -> str:
        """Given today's top items, return a markdown alpha idea breakdown."""
        if not rows:
            return ""

        items_text = "\n\n".join(
            f"### {row.get('title', '')}\n"
            f"来源：{row.get('source', '')} | 分类：{row.get('category', '')}\n"
            f"摘要：{row.get('one_line_summary') or row.get('abstract') or row.get('raw_text', '')[:400]}"
            for row in rows[:8]
        )

        prompt = f"""今天的量化情报如下：

{items_text}

---

请从上面的内容中提炼一个最有意思的 alpha idea，并拆解它的完整思路。

输出格式：

{{
  "alpha_name": "这个 alpha 的简短名字（不超过 20 字）",
  "source_item": "来自哪篇论文 / 帖子的启发",
  "hypothesis": "核心假设是什么：市场为什么会存在这个 alpha？",
  "signal_construction": "如何构建信号：用什么数据、什么频率、什么计算方法",
  "backtest_plan": "回测计划：资产池、时间段、因子中性化、换手控制、成本假设",
  "risks": "主要风险：容量、拥挤、数据可得性、过拟合",
  "next_step": "今天可以做的第一步：具体到数据来源和代码入口"
}}

只输出 JSON，全部中文。"""

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是资深量化研究员，专门从研究材料中提炼可执行的 alpha 想法。只输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            idea = _extract_json(content)
            return _render_alpha_idea(idea)
        except Exception as exc:
            return f"> Alpha idea 生成失败：{exc}"

    def generate_daily_crypto_alpha(
        self, rows: list[dict[str, Any]], date_str: str
    ) -> dict[str, Any]:
        """Generate a structured daily crypto alpha idea backed by today's content."""
        crypto_rows = [
            r for r in rows
            if str(r.get("category", "")).lower() == "crypto quant"
            or any(kw in (r.get("title", "") + r.get("one_line_summary", "")).lower()
                   for kw in ("crypto", "bitcoin", "btc", "ethereum", "eth", "defi",
                              "on-chain", "blockchain", "perpetual", "funding rate",
                              "liquidation", "binance", "bybit", "altcoin"))
        ]
        candidates = crypto_rows if len(crypto_rows) >= 2 else rows
        top = sorted(candidates, key=lambda r: float(r.get("final_score", 0)), reverse=True)[:12]

        items_text = "\n\n".join(
            f"### [{i+1}] {r.get('display_title') or r.get('title', '')}\n"
            f"来源：{r.get('source', '')} | 类型：{r.get('source_type', '')} | 分类：{r.get('category', '')}\n"
            f"摘要：{r.get('tldr') or r.get('one_line_summary') or r.get('abstract') or r.get('raw_text', '')[:350]}\n"
            f"URL：{r.get('reference_url') or r.get('url', '')}"
            for i, r in enumerate(top)
        )

        context_note = (
            f"（今日共找到 {len(crypto_rows)} 条 Crypto 相关内容，从中选取最相关条目）"
            if len(crypto_rows) >= 2
            else f"（今日 Crypto 专项内容较少，综合全类别 {len(top)} 条高分内容推断 Crypto alpha）"
        )

        prompt = f"""日期：{date_str}
{context_note}

今日量化情报精选如下：

{items_text}

---

你是专注加密货币的量化研究员。请根据以上内容，提炼一个今日最值得测试的 Crypto Alpha Idea。
要求：
- Alpha 必须有可获取的数据支撑（币安/Bybit OHLCV、链上数据、资金费率等皆可）
- 信号逻辑要具体到频率、时间窗口、触发条件
- 回测方法要明确（资产池、时间段、评估指标）
- supporting_sources 必须来自上方内容列表（标题和 URL 对应原文）

输出严格 JSON，全部字段必须有值：
{{
  "alpha_name": "不超过 20 字的 alpha 名称",
  "hypothesis": "一句话：市场为什么存在这个机会，谁是对手盘",
  "signal_logic": "具体信号：数据字段、计算方式、触发条件、持仓方向",
  "data_needed": ["数据来源 1（具体到交易所/链/API）", "数据来源 2"],
  "backtest_approach": "回测资产池、时间窗口、频率、止损、评估指标（夏普/最大回撤等）",
  "supporting_sources": [
    {{"title": "来自上方列表的文章标题", "url": "对应的原文 URL", "why": "这条内容如何支持这个 alpha"}}
  ],
  "risk_factors": ["风险 1", "风险 2", "风险 3"],
  "confidence": "high 或 medium 或 low",
  "confidence_reason": "一句话说明信心来源或局限",
  "quick_start": "今天可以立即做的第一步（具体到数据下载命令或代码思路）"
}}

只输出 JSON，不要有任何解释文字。"""

        reasoner_model = (
            os.environ.get("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner").strip()
            or "deepseek-reasoner"
        )
        payload = {
            "model": reasoner_model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是专注加密货币量化的资深研究员，擅长从信息流中发现可测试的 alpha。只输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        result = _extract_json(content)
        result["model"] = reasoner_model
        result["date"] = date_str
        return result

    def _prompt(self, item: Item, score: Score) -> str:
        body = truncate(item.readable_text, self.config.max_input_chars)
        arxiv_html = _arxiv_html_url(item.url)
        figure_hint = (
            f"\narXiv HTML 版（含原图）：{arxiv_html}" if arxiv_html else ""
        )
        source_hint = _source_type_hint(item.source_type)
        return f"""请按系统指令处理以下内容。{source_hint}

元数据：
- 标题：{item.title}
- 来源：{item.source}
- 来源类型：{source_type_zh(item.source_type)}
- 分类：{item.category}
- 评分：{score.final_score:.2f}
- URL：{item.url}{figure_hint}

原文：
{body}""".strip()


def _source_type_hint(source_type: str) -> str:
    if source_type == "paper":
        return (
            '\n\n【内容类型：学术论文】'
            '重点提取：研究问题、数据集、模型方法、关键量化指标（夏普、精度、收益等）、图表。'
            ' key_points[0]=核心方法或发现（含具体数字）；'
            'key_points[1]=量化可用性（数据要求、实现难度、可复现性）；'
            'key_points[2]=局限性批判（样本外、成本假设、过拟合风险）。'
            ' read_priority 以「样本外可复现性 + 量化直接可用性」为标准。'
        )
    if source_type in ("forum", "social", "x", "zhihu"):
        return (
            '\n\n【内容类型：社区讨论 / 社交媒体】'
            '重点提取：社区共识、实战经验、可操作建议、工具推荐、踩坑教训。'
            ' key_figures 必须返回 []（没有图表）。'
            ' key_points[0]=社区核心共识或最有价值的观点；'
            'key_points[1]=具体可操作的建议、方法或工具推荐；'
            'key_points[2]=争议点、注意事项或潜在风险。'
            ' core_idea 描述讨论的核心话题和社区主流观点，不要套用论文分析框架。'
            ' read_priority 以「讨论热度 + 实战价值」为标准，有可操作内容就给「高」，不要因为缺乏严格实验就降级。'
        )
    if source_type == "github":
        return (
            '\n\n【内容类型：GitHub 仓库】'
            '重点提取：工具功能、解决的量化问题、接入量化工作流的方式。'
            ' key_figures 必须返回 []。'
            ' key_points[0]=主要功能和解决的核心量化问题；'
            'key_points[1]=接入难度、依赖栈、代码质量（是否有测试、文档）；'
            'key_points[2]=局限性、维护活跃度、许可证风险。'
            ' possible_use_case 写具体的接入步骤，例如「替换现有回测框架的执行模块」。'
        )
    if source_type in ("blog", "news"):
        return (
            '\n\n【内容类型：博客 / 新闻】'
            '重点提取：作者核心论点、量化可操作性、支撑论据。'
            ' key_figures 返回 []（除非有具体数据图表）。'
            ' key_points[0]=作者最核心的量化观点；'
            'key_points[1]=支撑论点的证据或数据；'
            'key_points[2]=潜在偏差、幸存者偏差或需要独立验证的结论。'
        )
    return ""


def _arxiv_html_url(url: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d+)", url)
    if match:
        return f"https://arxiv.org/html/{match.group(1)}"
    return ""


def _extract_json(content: str) -> Any:
    """Parse JSON from model output that may contain <think> blocks or markdown fences."""
    # Strip reasoning-model think blocks
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    # Strip markdown code fences
    content = re.sub(r"```(?:json)?\s*", "", content)
    content = content.strip()
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Fall back: find first balanced { ... } or [ ... ]
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = content.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(content[start:], start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    return json.loads(content[start : i + 1])
    raise json.JSONDecodeError("No JSON object found", content, 0)


def _render_alpha_ideas(ideas: list[dict[str, Any]], model_name: str = "deepseek-reasoner") -> str:
    if not ideas:
        return ""
    blocks = []
    for i, idea in enumerate(ideas, start=1):
        blocks.append(
            f"**Idea {i}：{idea.get('alpha_name', '未命名')}**  "
            f"`{idea.get('idea_type', '')}` · 来源：{idea.get('source_item', '')}\n\n"
            f"{idea.get('core_insight', '')}"
        )
    body = "\n\n---\n\n".join(blocks)
    return f"*由 {model_name} 推理生成，来源：X / 论坛*\n\n{body}"


def _render_alpha_idea(idea: dict[str, Any]) -> str:
    lines = [
        f"### 💡 今日 Alpha Idea：{idea.get('alpha_name', '未命名')}",
        "",
        f"**灵感来源：** {idea.get('source_item', '')}",
        "",
        f"**核心假设**",
        f"{idea.get('hypothesis', '')}",
        "",
        f"**信号构建**",
        f"{idea.get('signal_construction', '')}",
        "",
        f"**回测计划**",
        f"{idea.get('backtest_plan', '')}",
        "",
        f"**主要风险**",
        f"{idea.get('risks', '')}",
        "",
        f"**今天可以做的第一步**",
        f"{idea.get('next_step', '')}",
    ]
    return "\n".join(lines)


def _validate_summary_payload(payload: dict[str, Any], item: Item) -> dict[str, Any]:
    key_points = payload.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = [str(key_points)]
    key_points = [str(p).strip() for p in key_points if str(p).strip()][:3]
    while len(key_points) < 3:
        key_points.append("需要进一步人工复核后再进入研究或生产判断。")

    priority = str(payload.get("read_priority", "中")).strip()
    if priority not in {"高", "中", "低"}:
        priority = "中"

    key_figures = payload.get("key_figures") or []
    if not isinstance(key_figures, list):
        key_figures = []
    arxiv_html = _arxiv_html_url(item.url)
    figures_md = _render_figures(key_figures, arxiv_html)

    return {
        "skip": False,
        "title_one_line": str(payload.get("title_one_line", "")).strip(),
        "one_line_summary": str(payload.get("one_line_summary", "")).strip(),
        "quant_impact": str(payload.get("quant_impact", "")).strip(),
        "core_idea": str(payload.get("core_idea", "")).strip(),
        "key_figures_md": figures_md,
        "key_points": key_points,
        "quant_relevance": str(payload.get("quant_relevance", "")).strip(),
        "possible_use_case": str(payload.get("possible_use_case", "")).strip(),
        "limitations": str(payload.get("limitations", "")).strip(),
        "read_priority": priority,
    }


def _render_figures(figures: list[Any], arxiv_html: str) -> str:
    if not figures:
        return ""
    lines = []
    for fig in figures:
        if not isinstance(fig, dict):
            continue
        ref = str(fig.get("ref", "")).strip()
        desc = str(fig.get("desc", "")).strip()
        if ref and desc:
            lines.append(f"- **{ref}**：{desc}")
    if not lines:
        return ""
    result = "\n".join(lines)
    if arxiv_html:
        result += f"\n- [原文图表（HTML版）]({arxiv_html})"
    return result
