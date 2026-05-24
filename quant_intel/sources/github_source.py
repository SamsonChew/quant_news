from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urlencode

from quant_intel.models import Item, utc_now_iso
from quant_intel.pipeline.normalize import clean_text, normalize_date, stable_hash
from quant_intel.sources.base import Source
from quant_intel.sources.http import fetch_text


GITHUB_SEARCH_API = "https://api.github.com/search/repositories"


class GitHubSource(Source):
    name = "GitHub"

    def __init__(self, queries: list[str], max_results: int = 15, fetch_readme: bool = False) -> None:
        self.queries = queries
        self.max_results = max_results
        self.fetch_readme = fetch_readme

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

    def _fetch_readme(self, full_name: str) -> str:
        """Fetch the raw README text for a GitHub repo. Returns '' on any error."""
        try:
            url = f"https://api.github.com/repos/{full_name}/readme"
            return fetch_text(url, headers={"Accept": "application/vnd.github.raw+json"})
        except Exception:
            return ""

    def _extract_readme_summary(self, readme: str) -> str:
        """Strip badge lines and keep up to (not including) the 4th ## section header."""
        if not readme:
            return ""
        lines = readme.splitlines()
        # Strip badge lines (lines starting with [![)
        lines = [line for line in lines if not line.strip().startswith("[![")]
        # Keep content up to (but not including) the 4th ## section header
        section_count = 0
        result_lines: list[str] = []
        for line in lines:
            if re.match(r"^##\s", line):
                section_count += 1
                if section_count >= 4:
                    break
            result_lines.append(line)
        return "\n".join(result_lines).strip()[:2000]

    def _repo_to_item(self, repo: dict) -> Item:
        full_name = clean_text(repo.get("full_name", ""))
        description = clean_text(repo.get("description", ""))
        topics = repo.get("topics") or []
        url = repo.get("html_url", "")
        updated_at = normalize_date(repo.get("updated_at")) or date.today().isoformat()
        text = f"{description} Topics: {', '.join(topics)}"

        if self.fetch_readme:
            readme = self._fetch_readme(full_name)
            summary = self._extract_readme_summary(readme)
            if summary:
                text = summary

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
