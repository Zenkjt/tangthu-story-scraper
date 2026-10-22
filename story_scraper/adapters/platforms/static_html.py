from __future__ import annotations

import re
from urllib.parse import urlparse

from ...core.adapter import AdapterNotApplicable
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class StaticHTMLFamilyAdapter(BaseStaticHTMLAdapter):
    """Conservative fallback for conventional static story/chapter HTML."""

    name = "static-html-family"
    family = "static-html"
    priority = 50

    _CHAPTER_PATTERNS = (
        re.compile(r"(?:chapter|chuong|chương)[-_ /]*(\d+)", re.I),
        re.compile(r"(?:part|phan|phần)[-_ /]*(\d+)", re.I),
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

    def build_index(self, url: str) -> Story:
        html = self.fetch_html(url)
        soup = self.soup(html)
        chapters = self._chapter_links(html, url)

        # A family adapter must reject pages that merely happen to contain
        # ordinary numbered links.
        if len(chapters) < 2:
            raise AdapterNotApplicable(
                "static HTML page does not expose a recognizable chapter index"
            )

        title = self.clean_text(soup.find("h1") or soup.find("title"))
        if not title:
            raise AdapterNotApplicable("static HTML story page has no title")

        author = ""
        author_node = soup.select_one(
            '[rel="author"], .author, .byline, [class*="author"]'
        )
        if author_node:
            author = self.clean_text(author_node)

        parsed = urlparse(url)
        story_id = f"{parsed.netloc}{parsed.path.rstrip('/')}" or parsed.netloc

        return Story(
            story_id=story_id,
            source_url=url,
            site=self.name,
            title=title,
            author=author,
            chapters=[
                Chapter(number=n, title=t, url=u)
                for n, t, u in chapters
            ],
            target_chapter_number=chapters[0][0],
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        html = self.fetch_html(story.source_url)
        known = {chapter.number for chapter in story.chapters}
        return [
            Chapter(number=n, title=t, url=u)
            for n, t, u in self._chapter_links(html, story.source_url)
            if n not in known
        ]

    def fetch_chapter(self, chapter: Chapter) -> tuple[ChapterContent, bool]:
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
