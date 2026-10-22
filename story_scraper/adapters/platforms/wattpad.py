from __future__ import annotations

import re
from urllib.parse import urlparse

from ...core.base_adapter import BasePlatformAdapter
from ...core.models import Chapter, Story


class WattpadAdapter(BasePlatformAdapter):
    """URL/manifest model for Wattpad.

    This first version deliberately separates Wattpad's story ID from its
    part/chapter ID. Network/API resolution is added independently.
    """

    name = "wattpad"
    family = "api-story"
    hosts = {"wattpad.com", "www.wattpad.com"}

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
    def chapter(
        *,
        number: int,
        title: str,
        url: str,
        external_id: str,
    ) -> Chapter:
        return Chapter(
            number=number,
            title=title,
            url=url,
            external_id=external_id,
        )

    def build_story_from_manifest(
        self,
        *,
        story_id: int,
        source_url: str,
        title: str,
        author: str,
        parts: list[dict],
        target_external_id: str | None = None,
    ) -> Story:
        chapters: list[Chapter] = []
        for number, part in enumerate(parts, start=1):
            external_id = str(part["id"])
            chapters.append(
                self.chapter(
                    number=number,
                    title=part.get("title") or f"Chương {number}",
                    url=part.get("url") or f"https://www.wattpad.com/{external_id}",
                    external_id=external_id,
                )
            )

        target = None
        if target_external_id is not None:
            for chapter in chapters:
                if chapter.external_id == str(target_external_id):
                    target = chapter.number
                    break

        return Story(
            story_id=str(story_id),
            source_url=source_url,
            site=self.name,
            title=title,
            author=author,
            chapters=chapters,
            target_chapter_number=target if target is not None else (
                chapters[0].number if chapters else None
            ),
        )
