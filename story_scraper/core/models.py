from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChapterStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"


@dataclass
class Chapter:
    number: int
    title: str
    url: str
    external_id: str | None = None
    status: ChapterStatus = ChapterStatus.PENDING
    content_hash: str | None = None


@dataclass
class Story:
    story_id: str
    source_url: str
    site: str
    title: str
    author: str
    chapters: list[Chapter] = field(default_factory=list)
    target_chapter_number: int | None = None
