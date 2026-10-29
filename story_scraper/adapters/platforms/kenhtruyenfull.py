from __future__ import annotations

import re
from urllib.parse import urlparse

from ...core.adapter import AdapterNotApplicable
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class KenhTruyenFullAdapter(BaseStaticHTMLAdapter):
    """Adapter for KenhTruyenFull / TruyenFull-style story pages.

    All source URL normalization and chapter-link construction stay inside
    this adapter. The registry only resolves the adapter; callers never
    construct KenhTruyenFull URLs themselves.
    """

    name = "kenhtruyenfull"
    family = "static-html"
    priority = 190

    _STORY_RE = re.compile(
        r"^/(?:truyen|doc-truyen)/(?P<slug>[^/]+?)(?:/chuong-(?P<chapter>\d+))?/?$",
        re.I,
    )

    _CHAPTER_RE = re.compile(
        r"^/doc-truyen/(?P<slug>[^/]+)/chuong-(?P<chapter>\d+)/?$",
        re.I,
    )

    @classmethod
    def matches(cls, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.netloc.casefold() == "kenhtruyenfull.com"
            and bool(cls._STORY_RE.match(parsed.path))
        )

    @classmethod
    def _match(cls, url: str):
        return cls._STORY_RE.match(urlparse(url).path)

    @classmethod
    def _target_chapter_number(cls, url: str) -> int | None:
        match = cls._match(url)
        if not match:
            return None
        value = match.group("chapter")
        return int(value) if value is not None else None

    def fetch_initial_target_on_register(self, story: Story) -> bool:
        return self._target_chapter_number(story.source_url) is not None

    def _story_url(self, url: str) -> str:
        parsed = urlparse(url)
        match = self._match(url)
        if not match:
            raise AdapterNotApplicable(
                f"Unsupported KenhTruyenFull URL: {url}"
            )
        return (
            f"{parsed.scheme or 'https'}://{parsed.netloc}"
            f"/truyen/{match.group('slug')}"
        )

    def _chapter_url(self, base_url: str, slug: str, number: int) -> str:
        parsed = urlparse(base_url)
        return (
            f"{parsed.scheme or 'https'}://{parsed.netloc}"
            f"/doc-truyen/{slug}/chuong-{number}"
        )

    def _chapter_links(
        self, html: str, base_url: str, slug: str
    ) -> list[tuple[int, str, str]]:
        soup = self.soup(html)
        result: list[tuple[int, str, str]] = []

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            parsed = urlparse(href)
            if parsed.netloc.casefold() != urlparse(base_url).netloc.casefold():
                continue

            match = self._CHAPTER_RE.match(parsed.path)
            if not match or match.group("slug").casefold() != slug.casefold():
                continue

            number = int(match.group("chapter"))
            title = self.clean_text(link) or f"Chương {number}"
            result.append((number, title, href.rstrip("/")))

        seen: set[str] = set()
        unique: list[tuple[int, str, str]] = []
        for number, title, href in result:
            key = href.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append((number, title, href))

        unique.sort(key=lambda item: (item[0], item[2]))
        return unique

    def _discover_cover_url(
        self, soup, base_url: str, title: str
    ) -> str | None:
        for selector, attr in (
            ('meta[property="og:image"]', "content"),
            ('meta[name="twitter:image"]', "content"),
            ('meta[name="twitter:image:src"]', "content"),
        ):
            node = soup.select_one(selector)
            value = node.get(attr) if node else None
            if value and not value.startswith("data:"):
                return self.absolute_url(base_url, value)

        cover_words = ("cover", "book-cover", "bookcover", "bia")
        for image in soup.find_all("img"):
            marker = " ".join(
                str(image.get(attr, ""))
                for attr in ("id", "class", "title", "alt")
            ).casefold()
            if any(word in marker for word in cover_words):
                for attr in (
                    "src",
                    "data-src",
                    "data-original",
                    "data-lazy-src",
                ):
                    value = image.get(attr)
                    if value and not value.startswith("data:"):
                        return self.absolute_url(base_url, value)

        normalized_title = self.clean_text(title).casefold()
        if normalized_title:
            for image in soup.find_all("img"):
                alt = self.clean_text(image.get("alt", ""))
                if alt and alt.casefold() == normalized_title:
                    for attr in (
                        "src",
                        "data-src",
                        "data-original",
                        "data-lazy-src",
                    ):
                        value = image.get(attr)
                        if value and not value.startswith("data:"):
                            return self.absolute_url(base_url, value)

        return None

    def _author(self, soup, title_node) -> str:
        label = soup.find(
            string=re.compile(r"^\s*Tác giả\s*:\s*$", re.I)
        )
        if label:
            parent = label.parent
            text = self.clean_text(parent)
            text = re.sub(
                r"^\s*Tác giả\s*:\s*",
                "",
                text,
                flags=re.I,
            ).strip()
            if text:
                return text

            next_node = parent.find_next()
            text = self.clean_text(next_node)
            if text:
                return text

        if title_node:
            for heading in title_node.find_all_previous(
                ["h2", "h3"], limit=3
            ):
                candidate = self.clean_text(heading)
                if candidate:
                    return candidate

        return ""

    def build_index(self, url: str) -> Story:
        if not self.matches(url):
            raise AdapterNotApplicable(
                f"Unsupported KenhTruyenFull URL: {url}"
            )

        story_url = self._story_url(url)
        html = self.fetch_html(story_url)
        soup = self.soup(html)

        title_node = soup.find("h1")
        title = self.clean_text(title_node)
        if not title:
            raise AdapterNotApplicable(
                "KenhTruyenFull story page has no title"
            )

        match = self._match(url)
        slug = match.group("slug")

        chapter_links = self._chapter_links(html, story_url, slug)
        if not chapter_links:
            raise AdapterNotApplicable(
                "KenhTruyenFull story page does not expose chapter links"
            )

        chapters = [
            Chapter(
                number=number,
                title=chapter_title,
                url=chapter_url,
                external_id=str(number),
            )
            for number, chapter_title, chapter_url in chapter_links
        ]

        story = Story(
            story_id=slug,
            source_url=url,
            site=self.name,
            title=title,
            author=self._author(soup, title_node),
            chapters=chapters,
            target_toc_index=1,
            index_url=story_url,
            cover_url=self._discover_cover_url(
                soup, story_url, title
            ),
        )

        story.normalize_toc()

        target_number = self._target_chapter_number(url)
        if target_number is not None:
            target = next(
                (
                    entry
                    for entry in story.chapters
                    if entry.number == target_number
                ),
                None,
            )
            if target is None:
                raise AdapterNotApplicable(
                    f"KenhTruyenFull chapter {target_number} "
                    f"is not present in the story index"
                )
            story.target_toc_index = target.toc_index
            story.registered_toc_index = target.toc_index

        return story

    def refresh_index(self, story: Story) -> Story:
        return self.build_index(story.index_url or story.source_url)

    def refresh_tail(self, story: Story) -> list[Chapter]:
        refreshed = self.refresh_index(story)
        known = {
            chapter.url.rstrip("/").casefold()
            for chapter in story.chapters
        }
        return [
            chapter
            for chapter in refreshed.chapters
            if chapter.url.rstrip("/").casefold() not in known
        ]

    def fetch_chapter(
        self, chapter: Chapter
    ) -> tuple[ChapterContent, bool]:
        html = self.fetch_html(chapter.url)
        title, content, complete = self.parse_chapter_page(
            html, chapter.url, chapter.number
        )
        if title:
            chapter.title = title
        return content, complete

    def parse_chapter_page(
        self,
        html: str,
        url: str,
        chapter_number: int | None,
    ) -> tuple[str, ChapterContent, bool]:
        soup = self.soup(html)

        heading = (
            soup.select_one(".chapter-title, .title-chapter")
            or soup.find("h1")
        )
        title = self.clean_text(heading)

        container = soup.select_one(
            ".chapter-c, .chapter-content, .reading-content, "
            ".content-chapter, #chapter-c"
        )
        if container is None and heading:
            container = heading.find_parent(["article", "main"])
        if container is None:
            container = soup.find("main") or soup.body
        if container is None:
            return title, ChapterContent(""), True

        for node in container.select(
            "script, style, nav, form, button, input, select, "
            "footer, .rating, .menu, .navigation, .comments, "
            ".comment, .ads, .advertisement"
        ):
            node.decompose()

        prefix = f"toc-{chapter_number or 1}"
        content = self.extract_images(container, url, prefix)
        return title, content, True
