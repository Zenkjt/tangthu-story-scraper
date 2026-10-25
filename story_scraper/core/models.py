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
    """One ordered entry in the source TOC.

    ``toc_index`` is Tàng Thư's canonical navigation key.
    ``number`` is only the source's chapter number, when the source has one.
    """

    number: int | None
    title: str
    url: str
    status: ChapterStatus = ChapterStatus.PENDING
    content_hash: str | None = None
    external_id: str | None = None
    toc_index: int = 0
    kind: str = "chapter"

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "status": self.status.value,
            "content_hash": self.content_hash,
            "external_id": self.external_id,
            "toc_index": self.toc_index,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], fallback_toc_index: int = 0) -> "Chapter":
        number = data.get("number")
        return cls(
            int(number) if number is not None else None,
            data.get("title", ""),
            data["url"],
            ChapterStatus(data.get("status", "pending")),
            data.get("content_hash"),
            data.get("external_id"),
            int(data.get("toc_index", fallback_toc_index)),
            data.get("kind", "chapter"),
        )


@dataclass
class Story:
    story_id: str
    source_url: str
    site: str
    title: str = ""
    author: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    target_toc_index: int | None = None
    registered_toc_index: int | None = None
    index_url: str | None = None

    def normalize_toc(self) -> None:
        """Assign stable 1-based TOC positions without using source chapter numbers."""
        for index, entry in enumerate(self.chapters, 1):
            entry.toc_index = index

    def entry_at(self, toc_index: int | None) -> Chapter | None:
        if toc_index is None:
            return None
        return next(
            (entry for entry in self.chapters if entry.toc_index == int(toc_index)),
            None,
        )

    @property
    def target_entry(self) -> Chapter | None:
        return self.entry_at(self.target_toc_index)

    # Backward-compatible read/write bridge for old cache/UI data.
    @property
    def target_chapter_number(self) -> int | None:
        entry = self.target_entry
        return entry.number if entry is not None else None

    @target_chapter_number.setter
    def target_chapter_number(self, value: int | None) -> None:
        if value is None:
            self.target_toc_index = None
            return
        entry = next(
            (item for item in self.chapters if item.number == int(value)),
            None,
        )
        self.target_toc_index = entry.toc_index if entry is not None else None

    def as_dict(self) -> dict[str, Any]:
        self.normalize_toc()
        return {
            "story_id": self.story_id,
            "source_url": self.source_url,
            "site": self.site,
            "title": self.title,
            "author": self.author,
            "chapters": [c.as_dict() for c in self.chapters],
            "target_toc_index": self.target_toc_index,
            "registered_toc_index": self.registered_toc_index,
            "index_url": self.index_url,
            # Keep old field so older UI/cache readers do not break.
            "target_chapter_number": self.target_chapter_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        chapters = [
            Chapter.from_dict(c, index)
            for index, c in enumerate(data.get("chapters", []), 1)
        ]
        story = cls(
            data["story_id"],
            data["source_url"],
            data["site"],
            data.get("title", ""),
            data.get("author", ""),
            chapters,
            None,
            int(data["registered_toc_index"]) if data.get("registered_toc_index") is not None else None,
            data.get("index_url"),
        )
        story.normalize_toc()

        target = data.get("target_toc_index")
        if target is not None:
            story.target_toc_index = int(target)
        elif data.get("target_chapter_number") is not None:
            # Migrate old state keyed by source chapter number.
            story.target_chapter_number = int(data["target_chapter_number"])
        elif "current_index" in data:
            index = int(data.get("current_index", 0))
            if 0 <= index < len(chapters):
                story.target_toc_index = index + 1
        elif chapters:
            story.target_toc_index = chapters[0].toc_index

        return story
