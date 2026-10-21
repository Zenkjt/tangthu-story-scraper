from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse
from .models import Chapter, Story


class SiteAdapter(ABC):
    """Public adapter contract used by the Story Scraper engine."""

    name: str
    family: str = "custom"

    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build_index(self, url: str) -> Story:
        """Build initial story metadata + chapter manifest without downloading chapters."""
        raise NotImplementedError

    @abstractmethod
    def refresh_tail(self, story: Story) -> list[Chapter]:
        """Inspect only the tail and return new/changed chapter descriptors."""
        raise NotImplementedError

    @abstractmethod
    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        """Return chapter content and the site's completion signal."""
        raise NotImplementedError

    def is_chapter_complete(self, chapter: Chapter, content: str) -> bool:
        """Optional final normalization hook for adapters with local completion rules."""
        return chapter.status.value == "complete"

    @staticmethod
    def host(url: str) -> str:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
