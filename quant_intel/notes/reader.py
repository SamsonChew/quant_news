from __future__ import annotations

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


def load_notes(notes_dir: Path) -> list[dict[str, Any]]:
    """Read all YYYY-MM-DD.md notes and return structured list sorted newest first."""
    if not notes_dir.exists():
        return []
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    notes = []
    for f in sorted(notes_dir.glob("*.md"), reverse=True):
        if not pattern.match(f.stem):
            continue
        try:
            body = f.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        title = _extract_title(body) or f.stem
        body_html = _render_md(body)
        notes.append({
            "date": f.stem,
            "title": title,
            "body": body,
            "body_html": body_html,
        })
    return notes


def _render_md(text: str) -> str:
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
    return md.convert(text)


def _extract_title(body: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""
