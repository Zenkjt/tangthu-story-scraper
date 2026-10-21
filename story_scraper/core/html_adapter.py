from __future__ import annotations

from abc import ABC
from html import unescape
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .base_adapter import BasePlatformAdapter


class BaseStaticHTMLAdapter(BasePlatformAdapter, ABC):
    """Generic mechanics for story sites exposed as server-rendered HTML."""

    family = "static-html"
    user_agent = "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)"

    def fetch_html(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def clean_text(node) -> str:
        if node is None:
            return ""
        return " ".join(unescape(node.get_text(" ", strip=True)).split())

    @staticmethod
    def absolute_links(base_url: str, nodes) -> list[str]:
        return [BasePlatformAdapter.absolute_url(base_url, node.get("href", ""))
                for node in nodes if node.get("href")]
