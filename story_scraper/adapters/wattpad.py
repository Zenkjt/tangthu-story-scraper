from __future__ import annotations

from ..core.html_adapter import BaseStaticHTMLAdapter
from ..core.models import Story, Chapter


class WattpadAdapter(BaseStaticHTMLAdapter):
    """Wattpad-specific extraction; no Wattpad rules belong in core."""

    name = "wattpad"
    family = "wattpad"
    hosts = {"wattpad.com"}

    @classmethod
    def matches(cls, url: str) -> bool:
        host = cls.host(url)
        return host == "wattpad.com" or host.endswith(".wattpad.com")

    def build_index(self, url: str) -> Story:
        raise NotImplementedError("Wattpad extraction is the next implementation step.")

    def refresh_tail(self, story: Story) -> list[Chapter]:
        raise NotImplementedError

    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        raise NotImplementedError
