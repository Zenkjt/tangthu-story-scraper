from __future__ import annotations

import mimetypes
from abc import ABC
from html import unescape
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BasePlatformAdapter
from .models import ChapterAsset, ChapterContent


class BaseStaticHTMLAdapter(BasePlatformAdapter, ABC):
    """Generic mechanics for story sites exposed as server-rendered HTML."""

    family = "static-html"
    user_agent = "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)"

    def fetch_html(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def fetch_asset(self, url: str) -> tuple[bytes, str]:
        request = Request(url, headers={"User-Agent": self.user_agent, "Referer": url})
        with urlopen(request, timeout=20) as response:
            media_type = response.headers.get_content_type()
            return response.read(), media_type

    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def clean_text(node) -> str:
        if node is None:
            return ""
        return " ".join(unescape(node.get_text(" ", strip=True)).split())

    @staticmethod
    def absolute_url(base_url: str, href: str) -> str:
        return urljoin(base_url, href)

    @staticmethod
    def absolute_links(base_url: str, nodes) -> list[str]:
        return [BaseStaticHTMLAdapter.absolute_url(base_url, node.get("href", ""))
                for node in nodes if node.get("href")]

    def extract_images(self, container, base_url: str, prefix: str) -> ChapterContent:
        assets: list[ChapterAsset] = []
        seen: set[str] = set()

        for index, image in enumerate(container.find_all("img"), start=1):
            source = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-original")
                or image.get("data-lazy-src")
            )
            if not source or source.startswith("data:"):
                continue

            asset_url = self.absolute_url(base_url, source)
            if asset_url in seen:
                continue
            seen.add(asset_url)

            try:
                payload, media_type = self.fetch_asset(asset_url)
            except Exception:
                continue

            extension = mimetypes.guess_extension(media_type) or ".bin"
            if extension == ".jpe":
                extension = ".jpg"
            filename = f"images/{prefix}-{index:03d}{extension}"
            assets.append(ChapterAsset(filename, payload, media_type))
            image["src"] = filename
            for attr in ("data-src", "data-original", "data-lazy-src"):
                image.attrs.pop(attr, None)

        return ChapterContent(container.decode_contents().strip(), assets)
