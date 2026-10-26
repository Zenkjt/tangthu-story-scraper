from __future__ import annotations

import io
import json
import re
from pathlib import PurePosixPath
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, Story


class WattpadAdapter(BaseStaticHTMLAdapter):
    name = "wattpad"
    family = "api-story"
    hosts = {"wattpad.com", "www.wattpad.com"}
    API_BASE = "https://www.wattpad.com/api/v3"
    STORYTEXT_BASE = "https://www.wattpad.com/apiv2/"

    _STORY_RE = re.compile(
        r"^/story/(?P<story_id>\d+)(?:-[^/]*)?/?$", re.I
    )
    _PART_RE = re.compile(
        r"^/(?P<part_id>\d+)(?:-[^/]*)?/?$", re.I
    )

    def __init__(self):
        self._part_to_story: dict[str, str] = {}
        self._story_content_zip: dict[str, bytes] = {}

    @classmethod
    def matches(cls, url):
        path = urlparse(url).path
        return cls.host(url) in cls.hosts and bool(
            cls._STORY_RE.match(path) or cls._PART_RE.match(path)
        )

    @classmethod
    def extract_ids(cls, url):
        path = urlparse(url).path
        match = cls._STORY_RE.match(path)
        if match:
            return int(match.group("story_id")), None

        match = cls._PART_RE.match(path)
        if match:
            return None, match.group("part_id")

        return None, None

    @staticmethod
    def _request_json(url):
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TangThuStoryScraper/1.0)"
                )
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _request_bytes(url):
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TangThuStoryScraper/1.0)"
                ),
                "Accept": "application/zip,application/octet-stream,*/*",
                "Accept-Encoding": "identity",
            },
        )
        with urlopen(request, timeout=60) as response:
            return response.read()

    def _fetch_story_content_zip(self, story_id: str) -> bytes:
        cached = self._story_content_zip.get(story_id)
        if cached is not None:
            return cached

        url = self.STORYTEXT_BASE + "?" + urlencode(
            {
                "m": "storytext",
                "group_id": story_id,
                "output": "zip",
            }
        )

        payload = self._request_bytes(url)

        try:
            with ZipFile(io.BytesIO(payload)) as archive:
                archive.testzip()
        except BadZipFile as exc:
            raise ValueError(
                f"Wattpad storytext ZIP is invalid for story {story_id}"
            ) from exc

        self._story_content_zip[story_id] = payload
        return payload

    @staticmethod
    def _chapter_html_from_zip(payload: bytes, chapter_id: str) -> str:
        with ZipFile(io.BytesIO(payload)) as archive:
            target = None

            for name in archive.namelist():
                if name.endswith("/"):
                    continue

                filename = PurePosixPath(name).name
                stem = PurePosixPath(filename).stem

                if (
                    name == chapter_id
                    or filename == chapter_id
                    or stem == chapter_id
                ):
                    target = name
                    break

            if target is None:
                raise ValueError(
                    "Wattpad storytext ZIP does not contain "
                    f"chapter {chapter_id}"
                )

            return archive.read(target).decode("utf-8")

    def fetch_story(self, source_url):
        story_id, target_part_id = self.extract_ids(source_url)

        if story_id is None:
            if target_part_id is None:
                raise ValueError(
                    f"Unsupported Wattpad URL: {source_url}"
                )

            part_data = self._request_json(
                f"{self.API_BASE}/story_parts/{target_part_id}"
            )
            story_id = int(part_data["groupId"])

        fields = (
            "id,title,url,user(name,username),"
            "parts(id,title,url,deleted,draft,createDate,modifyDate),"
            "numParts,cover"
        )

        data = self._request_json(
            f"{self.API_BASE}/stories/{story_id}?"
            + urlencode({"fields": fields})
        )

        parts = [
            part
            for part in data.get("parts", [])
            if not part.get("deleted") and not part.get("draft")
        ]

        chapters = [
            Chapter(
                number=index,
                title=part.get("title") or f"Chương {index}",
                url=part.get("url")
                or f"https://www.wattpad.com/{part['id']}",
                external_id=str(part["id"]),
            )
            for index, part in enumerate(parts, 1)
        ]

        story_id_text = str(data["id"])

        for chapter in chapters:
            self._part_to_story[chapter.external_id] = story_id_text

        target = next(
            (
                chapter
                for chapter in chapters
                if chapter.external_id == str(target_part_id)
            ),
            None,
        )

        story = Story(
            story_id=story_id_text,
            source_url=source_url,
            site=self.name,
            title=data.get("title", ""),
            author=(data.get("user") or {}).get("name", ""),
            chapters=chapters,
            target_toc_index=(
                target.toc_index if target is not None else 1
            ),
            index_url=data.get("url") or source_url,
        )

        story.normalize_toc()

        if target is not None:
            story.target_toc_index = target.toc_index

        return story

    def build_index(self, url):
        return self.fetch_story(url)

    def refresh_index(self, story: Story) -> Story:
        return self.fetch_story(story.source_url)

    def refresh_tail(self, story):
        refreshed = self.refresh_index(story)

        known = {
            chapter.external_id
            for chapter in story.chapters
            if chapter.external_id
        }

        return [
            chapter
            for chapter in refreshed.chapters
            if chapter.external_id not in known
        ]

    def fetch_chapter(self, chapter):
        chapter_id = str(chapter.external_id or "")

        if not chapter_id:
            raise ValueError(
                "Wattpad chapter is missing external_id"
            )

        story_id = self._part_to_story.get(chapter_id)

        if story_id is None:
            story_id = str(
                self._request_json(
                    f"{self.API_BASE}/story_parts/{chapter_id}"
                )["groupId"]
            )
            self._part_to_story[chapter_id] = story_id

        payload = self._fetch_story_content_zip(story_id)
        html = self._chapter_html_from_zip(payload, chapter_id)

        soup = self.soup(html)
        container = soup.body or soup

        return self.extract_images(
            container,
            chapter.url,
            prefix=f"chapter-{chapter.number}",
        )
