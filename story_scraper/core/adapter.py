from __future__ import annotations
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from .models import Story, Chapter


class SiteAdapter(ABC):
    name: str

    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build_index(self, url: str) -> Story:
        raise NotImplementedError

    @abstractmethod
    def refresh_tail(self, story: Story) -> list[Chapter]:
        """Refresh only the tail; return newly discovered/updated chapters."""
        raise NotImplementedError

    @abstractmethod
    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        """Return (content, complete)."""
        raise NotImplementedError

    @staticmethod
    def host(url: str) -> str:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
