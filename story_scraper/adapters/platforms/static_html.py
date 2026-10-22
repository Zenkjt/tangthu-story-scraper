from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from ...core.adapter import AdapterNotApplicable
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class StaticHTMLFamilyAdapter(BaseStaticHTMLAdapter):
    """Fallback for conventional static story/chapter HTML.

    Indexing follows pagination to discover chapter URLs only. Chapter content
    is fetched exclusively by ``fetch_chapter()`` when the engine triggers it.
    """

    name = "static-html-family"
    family = "static-html"
    priority = 50

    _CHAPTER_PATTERNS = (
        re.compile(r"(?:chapter|chuong|chương)[-_ /]*(\d+)", re.I),
        re.compile(r"(?:part|phan|phần)[-_ /]*(\d+)", re.I),
    )
    _PAGE_PATTERNS = (
        re.compile(r"/(?:trang|page)[-_ /]*(\d+)(?:/|$)", re.I),
        re.compile(r"[?&](?:page|trang)[=_-]?(\d+)", re.I),
    )

    @classmethod
    def matches(cls, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @classmethod
    def _chapter_number(cls, href: str, text: str) -> int | None:
        for value in (href, text):
            for pattern in cls._CHAPTER_PATTERNS:
                match = pattern.search(value or "")
                if match:
                    return int(match.group(1))
        return None

    @classmethod
    def _page_number(cls, href: str, text: str = "") -> int | None:
        for value in (href, text):
            for pattern in cls._PAGE_PATTERNS:
                match = pattern.search(value or "")
                if match:
                    return int(match.group(1))
        return None

    @classmethod
    def _is_pagination_link(cls, href: str, text: str) -> bool:
        lower = text.strip().lower()
        if lower in {"trang tiếp", "tiếp", "next", "next page", "sau", "cuối", "đầu", "first", "last"}:
            return True
        if cls._page_number(href, text) is not None:
            return True
        rel = (href or "").lower()
        return "/trang-" in rel or "page=" in rel or "trang=" in rel

    def _chapter_links(self, html: str, base_url: str) -> list[tuple[int, str, str]]:
        soup = self.soup(html)
        result: list[tuple[int, str, str]] = []
        seen: set[int] = set()

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            text = self.clean_text(link)
            number = self._chapter_number(href, text)
            if number is None or number in seen:
                continue
            seen.add(number)
            result.append((number, text or f"Chapter {number}", href))

        return sorted(result, key=lambda item: item[0])

    def _pagination_links(self, html: str, base_url: str) -> list[str]:
        soup = self.soup(html)
        result: list[str] = []
        seen: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            text = self.clean_text(link)
            if not self._is_pagination_link(href, text) or href in seen:
                continue
            seen.add(href)
            result.append(href)
        return result

    def _index_pages(self, url: str) -> list[tuple[str, str]]:
        """Fetch index/pagination pages only; never fetch chapter URLs here."""
        queue = [url]
        seen: set[str] = set()
        pages: list[tuple[str, str]] = []

        while queue:
            page_url = queue.pop(0)
            if page_url in seen:
                continue
            seen.add(page_url)
            html = self.fetch_html(page_url)
            pages.append((page_url, html))

            for next_url in self._pagination_links(html, page_url):
                if next_url not in seen:
                    queue.append(next_url)

        return pages

    def build_index(self, url: str) -> Story:
        pages = self._index_pages(url)
        first_html = pages[0][1]
        first_soup = self.soup(first_html)

        chapters: dict[int, tuple[str, str]] = {}
        for page_url, html in pages:
            for number, title, chapter_url in self._chapter_links(html, page_url):
                chapters.setdefault(number, (title, chapter_url))

        if len(chapters) < 2:
            raise AdapterNotApplicable(
                "static HTML page does not expose a recognizable chapter index"
            )

        title = self.clean_text(first_soup.find("h1") or first_soup.find("title"))
        if not title:
            raise AdapterNotApplicable("static HTML story page has no title")

        author = ""
        author_node = first_soup.select_one(
            '[rel="author"], .author, .byline, [class*="author"]'
        )
        if author_node:
            author = self.clean_text(author_node)

        parsed = urlparse(url)
        story_id = f"{parsed.netloc}{parsed.path.rstrip('/')}" or parsed.netloc
        ordered = sorted(chapters.items())

        return Story(
            story_id=story_id,
            source_url=url,
            site=self.name,
            title=title,
            author=author,
            chapters=[
                Chapter(number=n, title=t, url=u)
                for n, (t, u) in ordered
            ],
            target_chapter_number=ordered[0][0],
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        pages = self._index_pages(story.source_url)
        known = {chapter.number for chapter in story.chapters}
        found: dict[int, tuple[str, str]] = {}
        for page_url, html in pages:
            for number, title, chapter_url in self._chapter_links(html, page_url):
                if number not in known:
                    found[number] = (title, chapter_url)
        return [
            Chapter(number=n, title=t, url=u)
            for n, (t, u) in sorted(found.items())
        ]

    def fetch_chapter(self, chapter: Chapter) -> tuple[ChapterContent, bool]:
        # This is the only method in this adapter that fetches chapter content.
        html = self.fetch_html(chapter.url)
        soup = self.soup(html)

        heading = soup.find("h1") or soup.find("h2")
        title = self.clean_text(heading)
        if title:
            chapter.title = title

        container = (
            heading.find_parent(["article", "main", "div"])
            if heading else None
        )
        if container is None:
            container = soup.find("article") or soup.find("main") or soup.body
        if container is None:
            raise AdapterNotApplicable("chapter page has no readable content container")

        for node in container.select(
            "script, style, nav, form, button, input, select, footer, "
            ".rating, .menu, .navigation, .comments, .comment"
        ):
            node.decompose()

        content = self.extract_images(
            container, chapter.url, f"chapter-{chapter.number}"
        )
        if not self.clean_text(container):
            raise AdapterNotApplicable("chapter page has empty readable content")

        return content, True
