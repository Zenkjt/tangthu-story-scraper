from __future__ import annotations

import re
from abc import ABC
from html import unescape
from urllib.parse import urljoin, urlparse, urlunparse

from .adapter import SiteAdapter
from .models import Chapter, ChapterStatus


class BasePlatformAdapter(SiteAdapter, ABC):
    """Shared mechanics for adapters targeting the same web platform/family."""

    family = "platform"

    @staticmethod
    def normalize_url(url: str) -> str:
        parsed = urlparse(url.strip())
        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        if path != "/":
            path = path.rstrip("/")
        return urlunparse((parsed.scheme.lower() or "https", parsed.netloc.lower(), path, "", parsed.query, ""))

    @staticmethod
    def absolute_url(base_url: str, href: str) -> str:
        return BasePlatformAdapter.normalize_url(urljoin(base_url, href))

    @staticmethod
    def dedupe_urls(urls: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for url in urls:
            normalized = BasePlatformAdapter.normalize_url(url)
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def chapter_number(value: str, fallback: int | None = None) -> int | None:
        text = unescape(value)
        match = re.search(r"(?:chapter|chap|ch\.?|part|episode|ep\.?)\s*[-#:. ]*([0-9]+)", text, re.I)
        if match:
            return int(match.group(1))
        match = re.search(r"\b([0-9]+)\b", text)
        return int(match.group(1)) if match else fallback

    @staticmethod
    def merge_chapters(existing: list[Chapter], updates: list[Chapter]) -> list[Chapter]:
        """Merge descriptors without touching downloaded content hashes."""
        by_number = {chapter.number: chapter for chapter in existing}
        for incoming in updates:
            current = by_number.get(incoming.number)
            if current is None:
                by_number[incoming.number] = incoming
                continue
            current.title = incoming.title or current.title
            current.url = incoming.url or current.url
            # Never erase a locally known downloaded state during re-indexing.
            if current.status == ChapterStatus.PENDING:
                current.status = incoming.status
        return sorted(by_number.values(), key=lambda chapter: chapter.number)
