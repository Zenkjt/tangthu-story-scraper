from __future__ import annotations

import re
from urllib.parse import urlparse

from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class VnThuQuanAdapter(BaseStaticHTMLAdapter):
    """Configuration/thin adapter for vnthuquan's static HTML story pages."""

    name = "vnthuquan"
    family = "static-html"
    hosts = {"vnthuquan.net", "thuvien.vnthuquan.net"}

    _STORY_RE = re.compile(
        r"^/TacPham/(?P<slug>[^/]+?-\d+)(?:/chuong-(?P<chapter>\d+))?/?$",
        re.I,
    )

    @classmethod
    def matches(cls, url: str) -> bool:
        return cls.host(url) in cls.hosts and bool(
            cls._STORY_RE.match(urlparse(url).path)
        )

    def _story_url(self, url: str) -> str:
        parsed = urlparse(url)
        match = self._STORY_RE.match(parsed.path)
        if not match:
            raise ValueError(f"Unsupported vnthuquan URL: {url}")
        return (
            f"{parsed.scheme or 'https'}://{parsed.netloc}"
            f"/TacPham/{match.group('slug')}/"
        )

    def _chapter_links(
        self, html: str, base_url: str
    ) -> list[tuple[int, str, str]]:
        soup = self.soup(html)
        story_path = urlparse(self._story_url(base_url)).path.rstrip("/")
        result: list[tuple[int, str, str]] = []

        for link in soup.find_all("a", href=True):
            href = self.absolute_url(base_url, link["href"])
            path = urlparse(href).path.rstrip("/")
            if not path.startswith(story_path + "/chuong-"):
                continue
            match = re.search(r"/chuong-(\d+)$", path, re.I)
            if not match:
                continue
            number = int(match.group(1))
            title = self.clean_text(link) or f"Chương {number}"
            result.append((number, title, href))

        seen: set[int] = set()
        unique: list[tuple[int, str, str]] = []
        for item in result:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        return sorted(unique, key=lambda item: item[0])

    def build_index(self, url: str) -> Story:
        story_url = self._story_url(url)
        html = self.fetch_html(story_url)
        soup = self.soup(html)
        title_node = soup.find("h1")
        title = self.clean_text(title_node)

        author = ""
        if title_node:
            for heading in title_node.find_all_previous(["h2", "h3"], limit=3):
                candidate = self.clean_text(heading)
                if candidate:
                    author = candidate
                    break

        chapter_links = self._chapter_links(html, story_url)
        chapters = [
            Chapter(number=number, title=chapter_title, url=chapter_url)
            for number, chapter_title, chapter_url in chapter_links
        ]

        story_id = self._STORY_RE.match(urlparse(story_url).path).group("slug")
        entries = [
            Chapter(
                number=None,
                title=title or story_id,
                url=story_url,
                kind="page",
            )
        ] + chapters

        return Story(
            story_id=story_id,
            source_url=url,
            site=self.name,
            title=title,
            author=author,
            chapters=entries,
            target_toc_index=1,
            index_url=story_url,
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        index_url = story.index_url or story.source_url
        html = self.fetch_html(index_url)
        links = self._chapter_links(html, index_url)
        known = {chapter.url.rstrip("/") for chapter in story.chapters}
        return [
            Chapter(number=n, title=t, url=u)
            for n, t, u in links
            if u.rstrip("/") not in known
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
        self, html: str, url: str, chapter_number: int | None
    ) -> tuple[str, ChapterContent, bool]:
        soup = self.soup(html)
        heading = soup.find("h1")
        title = self.clean_text(heading)

        if heading:
            container = heading.find_parent(["article", "main", "div"])
        else:
            container = None
        if container is None:
            container = soup.find("main") or soup.body
        if container is None:
            return title, ChapterContent(""), True

        for node in container.select(
            "script, style, nav, form, button, input, select, footer, "
            ".rating, .menu, .navigation"
        ):
            node.decompose()

        prefix = f"toc-{chapter_number or 1}"
        content = self.extract_images(container, url, prefix)
        return title, content, True
