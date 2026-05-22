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

    def _prompt(self, item: Item, score: Score) -> str:
        body = truncate(item.readable_text, self.config.max_input_chars)
        arxiv_html = _arxiv_html_url(item.url)
        figure_hint = (
            f"\narXiv HTML 版（含原图）：{arxiv_html}" if arxiv_html else ""
        )
        return f"""请按系统指令处理以下内容。

元数据：
- 标题：{item.title}
- 来源：{item.source}
- 来源类型：{source_type_zh(item.source_type)}
- 分类：{item.category}
- 评分：{score.final_score:.2f}
- URL：{item.url}{figure_hint}

原文：
{body}""".strip()


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
