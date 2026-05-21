from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from quant_intel.i18n import category_zh, source_type_zh
from quant_intel.models import Item, Score
from quant_intel.pipeline.normalize import truncate


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
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是资深量化研究员，负责把论文、论坛、GitHub、知乎、X 的内容"
                        "压缩成老板和量化研究员都能快速阅读的中文情报。"
                        "必须只输出 JSON，不要输出 Markdown。"
                    ),
                },
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
        parsed = json.loads(content)
        return _validate_summary_payload(parsed)

    def _prompt(self, item: Item, score: Score) -> str:
        body = truncate(item.readable_text, self.config.max_input_chars)
        return f"""
请为下面这条量化情报生成中文结构化摘要。最终展示会统一成：
1. 这篇文章的太长不读
2. 核心价值，对我量化的工作能够提供什么样的帮助
3. 关键核心点 / 论文或帖子摘要
4. 原文链接

要求：
1. 只输出 JSON object。
2. one_line_summary 就是“太长不读”，不超过 80 个中文字符，并且必须使用中文。
3. technical_summary 用 3-5 句话，讲清楚方法、价值和限制。
4. key_points 必须是 3 条，适配论文、帖子、代码仓库或社交媒体内容。
5. quant_relevance 要说明它为什么和量化研究、交易、风控或工程有关。
6. possible_use_case 要具体，能落到研究、回测、因子、执行、风控或工具建设。
7. limitations 要诚实指出交易成本、样本外、数据、可复现性、过拟合或社交媒体噪音。
8. read_priority 只能是 高、中、低。

JSON schema:
{{
  "one_line_summary": "...",
  "technical_summary": "...",
  "key_points": ["...", "...", "..."],
  "quant_relevance": "...",
  "possible_use_case": "...",
  "limitations": "...",
  "read_priority": "高"
}}

元数据：
- 标题：{item.title}
- 来源：{item.source}
- 来源类型：{source_type_zh(item.source_type)}
- 分类：{category_zh(item.category)}
- 分数：{score.final_score}
- URL：{item.url}

原文：
{body}
""".strip()


def _validate_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    key_points = payload.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = [str(key_points)]
    key_points = [str(point).strip() for point in key_points if str(point).strip()][:3]
    while len(key_points) < 3:
        key_points.append("需要进一步人工复核后再进入研究或生产判断。")

    priority = str(payload.get("read_priority", "中")).strip()
    if priority not in {"高", "中", "低"}:
        priority = "中"

    return {
        "one_line_summary": str(payload.get("one_line_summary", "")).strip(),
        "technical_summary": str(payload.get("technical_summary", "")).strip(),
        "key_points": key_points,
        "quant_relevance": str(payload.get("quant_relevance", "")).strip(),
        "possible_use_case": str(payload.get("possible_use_case", "")).strip(),
        "limitations": str(payload.get("limitations", "")).strip(),
        "read_priority": priority,
    }
