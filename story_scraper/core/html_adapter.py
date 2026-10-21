from __future__ import annotations

from abc import ABC
from .base_adapter import BasePlatformAdapter


class BaseStaticHTMLAdapter(BasePlatformAdapter, ABC):
    """Common base for sites whose story/chapter structure is exposed in HTML."""

    family = "static-html"

    def fetch_html(self, url: str) -> str:
        raise NotImplementedError("HTTP transport belongs to the concrete adapter/runtime.")

    def parse_story_page(self, html: str, url: str):
        raise NotImplementedError

    def parse_chapter_page(self, html: str, url: str):
        raise NotImplementedError
