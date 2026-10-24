"""Stable view models for the future Story HTTP API."""

from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StoryChapterView:
    number: int
    title: str
    url: str
    status: str = "pending"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StoryView:
    story_id: str
    title: str
    author: str
    site: str
    source_url: str
    current_chapter: int | None
    total_chapters: int
    chapters: list[StoryChapterView]
    cover_url: str | None = None
    status: str = "ready"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["chapters"] = [chapter.as_dict() for chapter in self.chapters]
        return data
