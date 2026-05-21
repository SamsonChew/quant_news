from __future__ import annotations

import json
from datetime import date
from urllib.parse import urlencode

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, normalize_date, stable_hash
from quant_intel.sources.base import Source
from quant_intel.sources.http import fetch_text


GITHUB_SEARCH_API = "https://api.github.com/search/repositories"


class GitHubSource(Source):
    name = "GitHub"

    def __init__(self, queries: list[str], max_results: int = 15) -> None:
        self.queries = queries
        self.max_results = max_results

    def fetch(self) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()
        for query in self.queries:
            params = urlencode(
                {
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": self.max_results,
                }
            )
            payload = json.loads(fetch_text(f"{GITHUB_SEARCH_API}?{params}"))
            for repo in payload.get("items", []):
                item = self._repo_to_item(repo)
                if item.id in seen:
                    continue
                seen.add(item.id)
                items.append(item)
        return items

    def _repo_to_item(self, repo: dict) -> Item:
        full_name = clean_text(repo.get("full_name", ""))
        description = clean_text(repo.get("description", ""))
        topics = repo.get("topics") or []
        url = repo.get("html_url", "")
        updated_at = normalize_date(repo.get("updated_at")) or date.today().isoformat()
        text = f"{description} Topics: {', '.join(topics)}"
        return Item(
            id=stable_hash(["github", url or full_name]),
            source=self.name,
            source_type="github",
            title=full_name,
            url=url,
            authors=[repo.get("owner", {}).get("login", "")],
            published_at=updated_at,
            collected_at=utc_now_iso(),
            raw_text=text,
            abstract=description,
            content_hash=stable_hash([url or full_name, description]),
            tags=[str(topic) for topic in topics],
            metadata={
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "open_issues": repo.get("open_issues_count", 0),
            },
        )
