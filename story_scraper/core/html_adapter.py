from __future__ import annotations

import mimetypes
import time
from abc import ABC
from html import unescape
from http.client import IncompleteRead
from urllib.error import URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BasePlatformAdapter
from .models import ChapterAsset, ChapterContent


class BaseStaticHTMLAdapter(BasePlatformAdapter, ABC):
    """Generic mechanics for story sites exposed as server-rendered HTML."""

    family = "static-html"
    user_agent = "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)"

    def _read_url(self, request: Request) -> tuple[bytes, str]:
        last_error = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=20) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read(), charset
            except (IncompleteRead, URLError) as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

        raise last_error  # pragma: no cover

    def fetch_html(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        payload, charset = self._read_url(request)
        return payload.decode(charset, errors="replace")

    def fetch_asset(self, url: str) -> tuple[bytes, str]:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Referer": url,
                "Accept-Encoding": "identity",
            },
        )
        payload, _ = self._read_url(request)
        media_type = mimetypes.guess_type(url)[0] or "application/octet-stream"
        return payload, media_type

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
