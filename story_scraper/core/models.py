from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChapterStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"


@dataclass
class ChapterAsset:
    path: str
    content: bytes
    media_type: str


@dataclass
class ChapterContent:
    html: str
    assets: list[ChapterAsset] = field(default_factory=list)

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.html.encode("utf-8"))
        for asset in sorted(self.assets, key=lambda item: item.path):
            digest.update(asset.path.encode("utf-8"))
            digest.update(asset.media_type.encode("utf-8"))
            digest.update(asset.content)
        return digest.hexdigest()


@dataclass
class Chapter:
    number: int
    title: str
    url: str
    status: ChapterStatus = ChapterStatus.PENDING
    content_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"number": self.number, "title": self.title, "url": self.url,
                "status": self.status.value, "content_hash": self.content_hash}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chapter":
        return cls(int(data["number"]), data["title"], data["url"],
                   ChapterStatus(data.get("status", "pending")),
                   data.get("content_hash"))


@dataclass
class Story:
    story_id: str
    source_url: str
    site: str
    title: str = ""
    author: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    target_chapter_number: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"story_id": self.story_id, "source_url": self.source_url,
                "site": self.site, "title": self.title, "author": self.author,
                "chapters": [c.as_dict() for c in self.chapters],
                "target_chapter_number": self.target_chapter_number}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        chapters = [Chapter.from_dict(c) for c in data.get("chapters", [])]
        target = data.get("target_chapter_number")

        if target is None and "current_index" in data:
            index = int(data.get("current_index", 0))
            if 0 <= index < len(chapters):
                target = chapters[index].number

        if target is None and chapters and "target_chapter_number" not in data and "current_index" not in data:
            target = chapters[0].number

        return cls(data["story_id"], data["source_url"], data["site"],
                   data.get("title", ""), data.get("author", ""), chapters,
                   int(target) if target is not None else None)
