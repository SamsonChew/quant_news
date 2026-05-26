from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any

import markdown as markdown_lib

_MD_EXTS = [
    "tables",
    "fenced_code",
    "codehilite",
    "toc",
    "attr_list",
    "sane_lists",
]

_IMG_TAG_RE = re.compile(r'<img\b([^>]*?)\bsrc="([^"]+)"([^>]*?)>')
_WEEK_RE = re.compile(r"^week(\d+)_", re.IGNORECASE)

# Map filenames to friendly display info
_KNOWN_SUBTITLES: dict[str, str] = {
    "week1_report": "四条路径并行探索 → Bagging 融合 → 精度/召回双轴框架",
    "week1_quantalpha": "从 0 到「可演示」：内网 LLM × 自动因子挖掘系统",
}

_KNOWN_TITLES: dict[str, str] = {
    "week1_report": "DeepLOB Week 1",
    "week1_quantalpha": "QuantaAlpha Week 1",
}


def load_weekly_reports(weekly_dir: Path) -> list[dict[str, Any]]:
    """Scan weekly_dir for week*.md files, render to HTML, return sorted list."""
    if not weekly_dir.exists():
        return []
    files = sorted(weekly_dir.glob("week*.md"))
    reports = []
    for f in files:
        stem = f.stem
        try:
            html = _render_md(f, weekly_dir)
        except Exception as exc:
            print(f"[weekly] Failed to render {f.name}: {exc}")
            continue
        title = _KNOWN_TITLES.get(stem, _friendly_title(stem))
        subtitle = _KNOWN_SUBTITLES.get(stem, "")
        week_num = _week_num(stem)
        reports.append({
            "id": stem,
            "title": title,
            "subtitle": subtitle,
            "week": week_num,
            "filename": f.name,
            "html": html,
        })
    return reports


def _render_md(path: Path, base_dir: Path) -> str:
    text = path.read_text(encoding="utf-8")
    md = markdown_lib.Markdown(
        extensions=_MD_EXTS,
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "noclasses": True,
                "pygments_style": "default",
            },
            "toc": {"permalink": False},
        },
    )
    html = md.convert(text)
    return _IMG_TAG_RE.sub(lambda m: _embed_image(m, base_dir), html)


def _embed_image(match: re.Match, base_dir: Path) -> str:
    before, src, after = match.group(1), match.group(2), match.group(3)
    if src.startswith(("http://", "https://", "data:")):
        return match.group(0)
    img_path = (base_dir / src).resolve()
    if not img_path.is_file():
        return match.group(0)
    mime, _ = mimetypes.guess_type(str(img_path))
    mime = mime or "application/octet-stream"
    encoded = base64.b64encode(img_path.read_bytes()).decode("ascii")
    return f'<img{before}src="data:{mime};base64,{encoded}"{after}>'


def _week_num(stem: str) -> int:
    m = _WEEK_RE.match(stem)
    return int(m.group(1)) if m else 99


def _friendly_title(stem: str) -> str:
    """week1_report → Week 1 Report"""
    name = stem.replace("_", " ").title()
    return name
