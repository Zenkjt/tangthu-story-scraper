from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story


class WattpadAdapter(BaseStaticHTMLAdapter):
    """Wattpad adapter.

    Architecture:
      - V3 story endpoint: metadata + ordered part manifest.
      - V3 story_parts endpoint: chapter metadata when needed.
      - V2 storytext endpoint: actual content for ONE part.

    Wattpad's native part ID is stored in Chapter.external_id.
    Tàng Thư chapter.number remains the sequential local number.
    """

    name = "wattpad"
    family = "api-story"
    hosts = {"wattpad.com", "www.wattpad.com"}

    API_BASE = "https://www.wattpad.com/api/v3"
    STORYTEXT_BASE = "https://www.wattpad.com/apiv2/storytext"

    _STORY_RE = re.compile(r"^/story/(?P<story_id>\d+)(?:-[^/]*)?/?$", re.I)
    _PART_RE = re.compile(r"^/(?P<part_id>\d+)(?:-[^/]*)?/?$", re.I)

    @classmethod
    def matches(cls, url: str) -> bool:
        if cls.host(url) not in cls.hosts:
            return False
        path = urlparse(url).path
        return bool(cls._STORY_RE.match(path) or cls._PART_RE.match(path))

    @classmethod
    def extract_ids(cls, url: str) -> tuple[int | None, str | None]:
        path = urlparse(url).path

        match = cls._STORY_RE.match(path)
        if match:
            return int(match.group("story_id")), None

        match = cls._PART_RE.match(path)
        if match:
            return None, match.group("part_id")

        return None, None

    @staticmethod
    def _request_json(url: str) -> dict:
        request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)"},
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_story(self, source_url: str) -> Story:
        story_id, target_part_id = self.extract_ids(source_url)

        if story_id is None:
            if target_part_id is None:
                raise ValueError(f"Unsupported Wattpad URL: {source_url}")

            # Resolve chapter URL -> story ID through the part metadata endpoint.
            part = self._request_json(
                f"{self.API_BASE}/story_parts/{target_part_id}"
            )
            story_id = int(part["groupId"])

        fields = (
            "id,title,url,user(name,username),"
            "parts(id,title,url,deleted,draft,createDate,modifyDate),"
            "numParts,cover"
        )
        endpoint = (
            f"{self.API_BASE}/stories/{story_id}?"
            + urlencode({"fields": fields})
        )
        data = self._request_json(endpoint)

        parts = [
            part for part in data.get("parts", [])
            if not part.get("deleted") and not part.get("draft")
        ]

        chapters: list[Chapter] = []
        for number, part in enumerate(parts, start=1):
            external_id = str(part["id"])
            chapters.append(
                Chapter(
                    number=number,
                    title=part.get("title") or f"Chương {number}",
                    url=part.get("url") or f"https://www.wattpad.com/{external_id}",
                    external_id=external_id,
                )
            )

        target = None
        if target_part_id is not None:
            for chapter in chapters:
                if chapter.external_id == str(target_part_id):
                    target = chapter.number
                    break

        return Story(
            story_id=str(data["id"]),
            source_url=source_url,
            site=self.name,
            title=data.get("title", ""),
            author=(data.get("user") or {}).get("name", ""),
            chapters=chapters,
            target_chapter_number=target if target is not None else (
                chapters[0].number if chapters else None
            ),
        )

    def fetch_chapter(self, chapter: Chapter) -> tuple[ChapterContent, bool]:
        if not chapter.external_id:
            raise ValueError("Wattpad chapter is missing external_id")

        endpoint = (
            f"{self.STORYTEXT_BASE}?"
            + urlencode({"id": chapter.external_id})
        )

        html = self.fetch_html(endpoint)
        soup = self.soup(html)

        # /apiv2/storytext returns the chapter body itself, not a full page.
        # Preserve the returned HTML and normalize embedded images to EPUB assets.
        container = soup.body or soup
        content = self.extract_images(
            container,
            chapter.url,
            prefix=f"chapter-{chapter.number}",
        )
        return content, True

    def refresh_tail(self, story: Story) -> list[Chapter]:
        refreshed = self.fetch_story(story.source_url)
        known = {chapter.external_id for chapter in story.chapters}

        return [
            chapter
            for chapter in refreshed.chapters
            if chapter.external_id not in known
        ]
