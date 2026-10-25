from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import Chapter, ChapterStatus, Story


class StoryManifestStore:
    """Per-user/per-story TOC metadata; chapter content stays in the EPUB."""

    schema_version = 2

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def path_for(self, user_id: str, story_id: str) -> Path:
        return self.root / self._key(user_id) / f"{self._key(story_id)}.json"

    def load(self, user_id: str, story_id: str) -> Story | None:
        path = self.path_for(user_id, story_id)
        if not path.exists():
            return None
        return self._from_manifest(json.loads(path.read_text(encoding="utf-8")))

    def save(self, user_id: str, story: Story) -> None:
        story.normalize_toc()
        path = self.path_for(user_id, story.story_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._to_manifest(story), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)

    @classmethod
    def _to_manifest(cls, story: Story) -> dict[str, Any]:
        story.normalize_toc()
        return {
            "schema_version": cls.schema_version,
            "story_id": story.story_id,
            "source_url": story.source_url,
            "site": story.site,
            "title": story.title,
            "author": story.author,
            "target_toc_index": story.target_toc_index,
            "registered_toc_index": story.registered_toc_index,
            "index_url": story.index_url,
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "url": c.url,
                    "toc_index": c.toc_index,
                    "kind": c.kind,
                    "status": c.status.value,
                    "content_hash": c.content_hash,
                    **({"external_id": c.external_id} if c.external_id else {}),
                }
                for c in sorted(story.chapters, key=lambda entry: entry.toc_index)
            ],
        }

    @staticmethod
    def _from_manifest(data: dict[str, Any]) -> Story:
        chapters = []
        for index, item in enumerate(data.get("chapters", []), 1):
            number = item.get("number")
            chapters.append(
                Chapter(
                    number=int(number) if number is not None else None,
                    title=item.get("title", ""),
                    url=item["url"],
                    status=ChapterStatus(item.get("status", "pending")),
                    content_hash=item.get("content_hash"),
                    external_id=item.get("external_id"),
                    toc_index=int(item.get("toc_index", index)),
                    kind=item.get("kind", "chapter" if number is not None else "section"),
                )
            )
        story = Story(
            story_id=data["story_id"],
            source_url=data["source_url"],
            site=data["site"],
            title=data.get("title", ""),
            author=data.get("author", ""),
            chapters=chapters,
            target_toc_index=(
                int(data["target_toc_index"])
                if data.get("target_toc_index") is not None
                else None
            ),
            registered_toc_index=(
                int(data["registered_toc_index"])
                if data.get("registered_toc_index") is not None
                else None
            ),
            index_url=data.get("index_url"),
        )
        # Sort by the persisted TOC order before normalization, with the list
        # position as fallback for legacy manifests that had no toc_index.
        story.chapters.sort(key=lambda entry: entry.toc_index)
        story.normalize_toc()
        if story.target_toc_index is None:
            legacy_number = data.get("target_chapter_number")
            if legacy_number is not None:
                legacy_target = next(
                    (c for c in story.chapters if c.number == int(legacy_number)),
                    None,
                )
                if legacy_target is not None:
                    story.target_toc_index = legacy_target.toc_index
            if story.target_toc_index is None and story.chapters:
                story.target_toc_index = story.chapters[0].toc_index
        return story
