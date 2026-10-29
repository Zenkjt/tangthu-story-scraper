from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from ...core.adapter import AdapterNotApplicable
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class KenhTruyenFullAdapter(BaseStaticHTMLAdapter):
    """Adapter for KenhTruyenFull using lazy chapter traversal.

    KenhTruyenFull does not expose a complete TOC on the story page.
    A chapter page exposes the next-chapter URL, so the adapter keeps only
    the currently known chapter chain and extends it one chapter at a time.
    """

    name = "kenhtruyenfull"
    family = "static-html"
    priority = 190
    lazy_toc = True

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

    @classmethod
    def _chapter_match(cls, url: str):
        return cls._CHAPTER_RE.match(urlparse(url).path)

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

    @staticmethod
    def _script_value(html: str, variable: str) -> str | None:
        pattern = re.compile(
            rf'\bvar\s+{re.escape(variable)}\s*=\s*"((?:\\.|[^"])*)"\s*;',
            re.I,
        )
        match = pattern.search(html)
        if not match:
            return None
        raw = match.group(1)
        try:
            return json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            return raw.replace(r"\/", "/")

    def _discover_cover_url(
        self,
        soup,
        base_url: str,
        book_name: str,
        slug: str,
    ) -> str | None:
        """Try several generic cover signals instead of one site-specific selector."""

        def absolute(value: str | None) -> str | None:
            if not value or value.startswith("data:"):
                return None
            return self.absolute_url(base_url, value.strip())

        # 1. Explicit social/SEO metadata.
        for key in (
            ("meta", {"property": "og:image"}),
            ("meta", {"name": "twitter:image"}),
            ("meta", {"name": "twitter:image:src"}),
        ):
            node = soup.find(key[0], attrs=key[1])
            if node:
                value = absolute(node.get("content"))
                if value:
                    return value

        normalized_title = " ".join(book_name.casefold().split())
        normalized_slug = slug.casefold().replace("_", "-")

        best_url = None
        best_score = -1

        for image in soup.find_all("img"):
            source = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-original")
                or image.get("data-lazy-src")
                or image.get("data-srcset")
            )
            image_url = absolute(source)
            if not image_url:
                continue

            alt = self.clean_text(image.get("alt"))
            title = self.clean_text(image.get("title"))
            ident = " ".join(
                str(image.get(attr) or "")
                for attr in ("id", "class")
            ).casefold()
            text = " ".join((alt, title)).casefold()
            parsed = urlparse(image_url)
            filename = parsed.path.rsplit("/", 1)[-1].casefold()
            stem = re.sub(r"\.[a-z0-9]{2,5}$", "", filename)

            score = 0

            # Exact/near title match is a very strong cover signal.
            if normalized_title and " ".join(alt.casefold().split()) == normalized_title:
                score += 120
            elif normalized_title and normalized_title in " ".join(alt.casefold().split()):
                score += 80

            if normalized_title and normalized_title in text:
                score += 30

            # Common semantic cover markers.
            if any(
                marker in ident
                for marker in (
                    "cover",
                    "book-cover",
                    "bookcover",
                    "bia",
                    "thumb-book",
                    "book-image",
                )
            ):
                score += 90

            # KenhTruyenFull's actual pattern is typically /uploads/.../<slug>.jpg.
            if normalized_slug and normalized_slug in stem.replace("_", "-"):
                score += 70

            # Prefer images inside the book-information block.
            parent = image.parent
            parent_classes = ""
            if parent is not None:
                parent_classes = " ".join(
                    str(parent.get(attr) or "")
                    for attr in ("id", "class")
                ).casefold()
            if any(
                marker in parent_classes
                for marker in ("book-info", "book-detail", "story-info", "thong-tin", "info-book")
            ):
                score += 35

            if score > best_score:
                best_score = score
                best_url = image_url

        return best_url

    def _chapter_metadata(
        self, html: str, base_url: str, slug: str
    ) -> tuple[str, str, str, str | None]:
        book_name = self._script_value(html, "book_name") or ""
        chapter_title = self._script_value(html, "chapTitle") or ""
        url_book = self._script_value(html, "url_book") or ""
        url_chap = self._script_value(html, "url_chap") or ""

        author = ""
        cover_url = None

        soup = self.soup(html)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if not book_name:
                    book_name = str(item.get("name") or "").strip()
                if not author:
                    value = item.get("author")
                    if isinstance(value, dict):
                        author = str(value.get("name") or "").strip()
                    elif isinstance(value, str):
                        author = value.strip()
                if cover_url is None:
                    image = item.get("image")
                    if isinstance(image, dict):
                        image = image.get("url")
                    if isinstance(image, list):
                        image = image[0] if image else None
                    if image:
                        cover_url = self.absolute_url(base_url, str(image))

        if cover_url is None:
            cover_url = self._discover_cover_url(
                soup, base_url, book_name, slug
            )

        if not chapter_title:
            heading = (
                soup.select_one(".chapter-title, .title-chapter")
                or soup.find("h1")
            )
            chapter_title = self.clean_text(heading)

        return book_name, chapter_title, author, cover_url

    def _next_chapter(self, html: str, base_url: str, current_number: int):
        soup = self.soup(html)
        candidates: list[tuple[int, str, str]] = []

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            parsed = urlparse(href)
            if parsed.netloc.casefold() != urlparse(base_url).netloc.casefold():
                continue

            match = self._CHAPTER_RE.match(parsed.path)
            if not match:
                continue

            number = int(match.group("chapter"))
            if number <= current_number:
                continue

            title = self.clean_text(link) or f"Chương {number}"
            candidates.append((number, title, href.rstrip("/")))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[2]))
        return candidates[0]

    def _chapter_from_page(
        self,
        html: str,
        chapter_url: str,
        number: int,
    ) -> tuple[Chapter, tuple[int, str, str] | None, str, str, str | None]:
        base_url = chapter_url
        match = self._chapter_match(chapter_url)
        if not match:
            raise AdapterNotApplicable(
                f"Unsupported KenhTruyenFull chapter URL: {chapter_url}"
            )
        slug = match.group("slug")

        book_name, chapter_title, author, cover_url = self._chapter_metadata(
            html, base_url, slug
        )

        current = Chapter(
            number=number,
            title=chapter_title or f"Chương {number}",
            url=chapter_url.rstrip("/"),
            external_id=str(number),
        )
        next_chapter = self._next_chapter(html, base_url, number)
        return current, next_chapter, book_name, author, cover_url

    def build_index(self, url: str) -> Story:
        if not self.matches(url):
            raise AdapterNotApplicable(
                f"Unsupported KenhTruyenFull URL: {url}"
            )

        parsed = self._match(url)
        slug = parsed.group("slug")
        chapter_number = self._target_chapter_number(url)

        if chapter_number is None:
            chapter_number = 1

        chapter_url = self._chapter_url(url, slug, chapter_number)
        html = self.fetch_html(chapter_url)
        current, next_chapter, book_name, author, cover_url = (
            self._chapter_from_page(html, chapter_url, chapter_number)
        )

        if not book_name:
            book_name = slug.replace("-", " ").strip()

        chapters = [current]
        if next_chapter is not None:
            number, title, next_url = next_chapter
            chapters.append(
                Chapter(
                    number=number,
                    title=title,
                    url=next_url,
                    external_id=str(number),
                )
            )

        story = Story(
            story_id=slug,
            source_url=url,
            site=self.name,
            title=book_name,
            author=author,
            chapters=chapters,
            target_toc_index=1,
            index_url=chapter_url,
            cover_url=cover_url,
        )
        story.normalize_toc()

        story.target_toc_index = 1
        story.registered_toc_index = 1

        return story

    def refresh_index(self, story: Story) -> Story:
        refreshed = self.build_index(
            story.target_entry.url
            if story.target_entry is not None
            else story.current_entry.url
            if story.current_entry is not None
            else story.source_url
        )
        return refreshed

    def refresh_tail(self, story: Story) -> list[Chapter]:
        if not story.chapters:
            return []

        last = max(story.chapters, key=lambda entry: entry.toc_index)
        match = self._chapter_match(last.url)
        if not match:
            return []

        current_number = int(match.group("chapter"))
        html = self.fetch_html(last.url)
        next_chapter = self._next_chapter(html, last.url, current_number)
        if next_chapter is None:
            return []

        number, title, next_url = next_chapter
        existing_urls = {
            chapter.url.rstrip("/").casefold() for chapter in story.chapters
        }
        if next_url.rstrip("/").casefold() in existing_urls:
            return []

        return [
            Chapter(
                number=number,
                title=title,
                url=next_url,
                external_id=str(number),
            )
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

        if not title:
            title = self._script_value(html, "chapTitle") or ""

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
