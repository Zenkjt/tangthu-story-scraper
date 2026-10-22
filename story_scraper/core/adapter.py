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

    @abstractmethod
    def refresh_tail(self, story: Story) -> list[Chapter]:
        raise NotImplementedError

    @abstractmethod
    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        raise NotImplementedError

    def is_chapter_complete(self, chapter: Chapter, content: str) -> bool:
        return chapter.status.value == "complete"

    @staticmethod
    def host(url: str) -> str:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
