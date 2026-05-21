from __future__ import annotations

import urllib.request


DEFAULT_HEADERS = {
    "User-Agent": "quant-intel-bot/0.1 (+https://localhost)",
    "Accept": "application/json, application/atom+xml, application/rss+xml, text/xml, */*",
}


def fetch_text(url: str, timeout: int = 25, headers: dict[str, str] | None = None) -> str:
    request_headers = dict(DEFAULT_HEADERS)
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        encoding = "utf-8"
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].split(";")[0].strip()
        return raw.decode(encoding, errors="replace")
