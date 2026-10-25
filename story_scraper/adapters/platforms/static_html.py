from __future__ import annotations

import re
from urllib.parse import urlparse

from ...core.adapter import AdapterNotApplicable
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class StaticHTMLFamilyAdapter(BaseStaticHTMLAdapter):
    """Fallback for conventional static story HTML with an ordered TOC."""

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
    _SECTION_TEXT_PATTERNS = (
        re.compile(
            r"^(?:lời\s+(?:mở\s+đầu|tựa|giới\s+thiệu)|mở\s+đầu|"
            r"giới\s+thiệu|lời\s+giới\s+thiệu|prologue|epilogue|"
            r"preface|introduction|foreword|opening|afterword)$",
            re.I,
        ),
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
        if lower in {
            "trang tiếp", "tiếp", "next", "next page", "sau",
            "cuối", "đầu", "first", "last",
        }:
            return True
        if cls._page_number(href, text) is not None:
            return True
        rel = (href or "").lower()
        return "/trang-" in rel or "page=" in rel or "trang=" in rel

    @staticmethod
    def _same_story_path(story_url: str, href: str) -> bool:
        story = urlparse(story_url)
        candidate = urlparse(href)
        if candidate.netloc and candidate.netloc != story.netloc:
            return False
        story_path = story.path.rstrip("/")
        path = candidate.path.rstrip("/")
        return bool(story_path) and (
            path == story_path or path.startswith(story_path + "/")
        )

    @classmethod
    def _looks_like_toc_link(cls, link, href: str, text: str, story_url: str) -> bool:
        if not text or cls._is_pagination_link(href, text):
            return False
        if not cls._same_story_path(story_url, href):
            return False
        if cls._chapter_number(href, text) is not None:
            return True
        if cls._SECTION_TEXT_PATTERNS[0].match(text.strip()):
            return True

        # Prefer links inside the site's chapter/TOC containers for arbitrary
        # named sections such as "Đêm ấy", "Phần mở đầu", etc.
        node = link
        while node is not None and getattr(node, "name", None) not in {None, "body"}:
            classes = " ".join(node.get("class", []) or []).lower()
            node_id = str(node.get("id") or "").lower()
            marker = f"{classes} {node_id}"
            if any(token in marker for token in (
                "chapter", "chapters", "chuong", "chuong-list",
                "list-chapter", "list-chapters", "toc", "muc-luc",
            )):
                return True
            node = getattr(node, "parent", None)

        return False

    def _toc_links(self, html: str, base_url: str, story_url: str):
        soup = self.soup(html)
        result = []
        seen: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            href_key = href.rstrip("/")
            text = self.clean_text(link)
            if href_key in seen:
                continue
            if not self._looks_like_toc_link(link, href, text, story_url):
                continue

            seen.add(href_key)
            number = self._chapter_number(href, text)
            kind = "chapter" if number is not None else "section"
            result.append((number, text, href, kind))

        return result

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

    @classmethod
    def _story_index_url(cls, url: str) -> str:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts and re.search(
            r"^(?:chapter|chuong|chương|part|phan|phần)[-_ ]*\d+",
            parts[-1],
            re.I,
        ):
            root = "/" + "/".join(parts[:-1])
            if not root.endswith("/"):
                root += "/"
            return parsed._replace(path=root, query="", fragment="").geturl()
        return url

    def _index_pages(self, url: str) -> list[tuple[str, str]]:
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
        index_url = self._story_index_url(url)
        pages = self._index_pages(index_url)
        first_html = pages[0][1]
        first_soup = self.soup(first_html)

        parsed = urlparse(url)
        story_id = f"{parsed.netloc}{parsed.path.rstrip('/')}" or parsed.netloc

        title = self.clean_text(first_soup.find("h1") or first_soup.find("title"))
        if not title:
            raise AdapterNotApplicable("static HTML story page has no title")

        author = ""
        author_node = first_soup.select_one(
            '[rel="author"], .author, .byline, [class*="author"]'
        )
        if author_node:
            author = self.clean_text(author_node)

        entries: list[Chapter] = [
            Chapter(
                number=None,
                title=title,
                url=index_url,
                kind="page",
            )
        ]
        seen = {index_url.rstrip("/")}

        for page_url, html in pages:
            for number, entry_title, entry_url, kind in self._toc_links(
                html, page_url, url
            ):
                key = entry_url.rstrip("/")
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    Chapter(
                        number=number,
                        title=entry_title or (
                            f"Chương {number}" if number is not None else "Mục"
                        ),
                        url=entry_url,
                        kind=kind,
                    )
                )

        if len(entries) < 2:
            raise AdapterNotApplicable(
                "static HTML page does not expose a recognizable story TOC"
            )

        return Story(
            story_id=story_id,
            source_url=url,
            site=self.name,
            title=title,
            author=author,
            chapters=entries,
            target_toc_index=1,
            registered_toc_index=None,
            index_url=index_url,
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        pages = self._index_pages(story.index_url or story.source_url)
        known = {chapter.url.rstrip("/") for chapter in story.chapters}
        found: list[Chapter] = []

        for page_url, html in pages:
            for number, title, chapter_url, kind in self._toc_links(
                html, page_url, story.source_url
            ):
                if chapter_url.rstrip("/") in known:
                    continue
                known.add(chapter_url.rstrip("/"))
                found.append(
                    Chapter(
                        number=number,
                        title=title,
                        url=chapter_url,
                        kind=kind,
                    )
                )

        return found

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
            raise AdapterNotApplicable("page has no readable content container")

        for node in container.select(
            "script, style, nav, form, button, input, select, footer, "
            ".rating, .menu, .navigation, .comments, .comment"
        ):
            node.decompose()

        content = self.extract_images(
            container, chapter.url, f"toc-{chapter.toc_index or 1}"
        )
        if not self.clean_text(container):
            raise AdapterNotApplicable("page has empty readable content")

        return content, True
