from __future__ import annotations
from urllib.parse import urlparse
from ..core.adapter import SiteAdapter
from ..core.models import Story, Chapter, ChapterStatus


class WattpadAdapter(SiteAdapter):
    """
    Adapter contract only.

    The DOM/API extraction belongs here; the core engine must never contain
    Wattpad-specific selectors or URLs.
    """

    name = "wattpad"
    hosts = {"wattpad.com"}

    @classmethod
    def matches(cls, url: str) -> bool:
        host = cls.host(url)
        return host == "wattpad.com" or host.endswith(".wattpad.com")

    def build_index(self, url: str) -> Story:
        raise NotImplementedError(
            "Implement Wattpad extraction here; core engine is ready."
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        raise NotImplementedError

    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        raise NotImplementedError
