from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChapterStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"


@dataclass
class Chapter:
    number: int
    title: str
    url: str
    status: ChapterStatus = ChapterStatus.PENDING
    content_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "status": self.status.value,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chapter":
        return cls(
            number=int(data["number"]),
            title=data["title"],
            url=data["url"],
            status=ChapterStatus(data.get("status", "pending")),
            content_hash=data.get("content_hash"),
        )


@dataclass
class Story:
    story_id: str
    source_url: str
    site: str
    title: str = ""
    author: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    current_index: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "source_url": self.source_url,
            "site": self.site,
            "title": self.title,
            "author": self.author,
            "chapters": [c.as_dict() for c in self.chapters],
            "current_index": self.current_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        return cls(
            story_id=data["story_id"],
            source_url=data["source_url"],
            site=data["site"],
            title=data.get("title", ""),
            author=data.get("author", ""),
            chapters=[Chapter.from_dict(c) for c in data.get("chapters", [])],
            current_index=int(data.get("current_index", 0)),
        )
