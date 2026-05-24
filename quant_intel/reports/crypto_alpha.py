from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_intel.models import utc_now_iso


def save_crypto_alpha(alpha: dict[str, Any], date_str: str, output_dir: Path) -> Path:
    alpha_dir = output_dir / "alpha"
    alpha_dir.mkdir(parents=True, exist_ok=True)
    alpha["generated_at"] = utc_now_iso()
    alpha["date"] = date_str
    path = alpha_dir / f"{date_str}.json"
    path.write_text(json.dumps(alpha, ensure_ascii=False, indent=2), encoding="utf-8")
    (alpha_dir / "latest.json").write_text(
        json.dumps(alpha, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_alpha_history(output_dir: Path, days: int = 30) -> list[dict[str, Any]]:
    alpha_dir = output_dir / "alpha"
    if not alpha_dir.exists():
        return []
    files = sorted(alpha_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"), reverse=True)
    history = []
    for f in files[:days]:
        try:
            history.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return history


def load_latest_alpha(output_dir: Path) -> dict[str, Any] | None:
    latest = output_dir / "alpha" / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None
