from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse

from .models import Chapter, Story


class AdapterNotApplicable(Exception):
    """Adapter candidate cannot handle this URL/site."""


class SiteAdapter(ABC):
    name: str
    family: str = "custom"
    priority: int = 100

    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    @classmethod
    def probe(cls, url: str) -> bool:
        return cls.matches(url)

    @abstractmethod
    def build_index(self, url: str) -> Story:
        raise NotImplementedError

    def refresh_index(self, story: Story) -> Story:
        """Return a complete fresh source TOC snapshot."""
        return self.build_index(story.index_url or story.source_url)

    def refresh_tail(self, story: Story) -> list[Chapter]:
        """Legacy compatibility; full refresh is now the canonical path."""
        refreshed = self.refresh_index(story)
        known = {
            (entry.external_id, entry.url.rstrip("/"))
            for entry in story.chapters
        }
        return [
            entry
            for entry in refreshed.chapters
            if (entry.external_id, entry.url.rstrip("/")) not in known
        ]

    def fetch_initial_target_on_register(self, story: Story) -> bool:
        """Whether registration should immediately fetch the selected target."""
        return False

    @abstractmethod
    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        raise NotImplementedError

    def is_chapter_complete(self, chapter: Chapter, content: str) -> bool:
        return chapter.status.value == "complete"

    @staticmethod
    def host(url: str) -> str:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
