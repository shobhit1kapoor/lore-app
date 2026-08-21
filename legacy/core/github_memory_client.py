"""GitHub Contents API adapter for versioned LORE memory documents."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from config import GITHUB_MEMORY_BRANCH, GITHUB_MEMORY_REPOSITORY, GITHUB_OWNER, GITHUB_TOKEN

logger = logging.getLogger("lore.github_memory")


class GitHubMemoryClient:
    """Expose the small wiki-like interface consumed by :class:`MemoryStore`."""

    def __init__(self, client: httpx.Client | None = None, trace_id: str | None = None) -> None:
        if not (GITHUB_TOKEN and GITHUB_OWNER and GITHUB_MEMORY_REPOSITORY):
            raise RuntimeError("GitHub memory is not configured")
        self.trace_id = trace_id
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

    @property
    def _repository_path(self) -> str:
        return f"/repos/{GITHUB_OWNER}/{GITHUB_MEMORY_REPOSITORY}"

    @staticmethod
    def _path_for_slug(slug: str) -> str:
        return "LORE-INDEX.md" if slug == "LORE-INDEX" else f"memories/{slug}.md"

    def list_wiki_pages(self) -> list[str]:
        response = self._client.get(f"{self._repository_path}/contents/memories", params={"ref": GITHUB_MEMORY_BRANCH})
        if response.status_code == 404:
            return []
        self._raise_for_status(response, "list memory documents")
        items = response.json()
        return [item["name"].removesuffix(".md") for item in items if item.get("type") == "file" and item.get("name", "").endswith(".md")]

    def get_wiki_page(self, slug: str) -> str | None:
        response = self._client.get(f"{self._repository_path}/contents/{self._path_for_slug(slug)}", params={"ref": GITHUB_MEMORY_BRANCH})
        if response.status_code == 404:
            return None
        self._raise_for_status(response, f"read memory document {slug}")
        body = response.json()
        encoded = body.get("content", "").replace("\n", "")
        return base64.b64decode(encoded).decode("utf-8")

    def create_wiki_page(self, slug: str, _title: str, content: str) -> None:
        self._put(slug, content, f"Create LORE memory {slug}")

    def update_wiki_page(self, slug: str, content: str) -> None:
        path = self._path_for_slug(slug)
        existing = self._client.get(f"{self._repository_path}/contents/{path}", params={"ref": GITHUB_MEMORY_BRANCH})
        self._raise_for_status(existing, f"read memory document {slug}")
        sha = existing.json().get("sha")
        self._put(slug, content, f"Update LORE memory {slug}", sha=sha)

    def _put(self, slug: str, content: str, message: str, sha: str | None = None) -> None:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": GITHUB_MEMORY_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        response = self._client.put(f"{self._repository_path}/contents/{self._path_for_slug(slug)}", json=payload)
        self._raise_for_status(response, f"write memory document {slug}")

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.is_success:
            return
        logger.warning("GitHub memory request failed during %s with status %s", action, response.status_code)
        raise RuntimeError(f"GitHub memory failed to {action} (HTTP {response.status_code})")
