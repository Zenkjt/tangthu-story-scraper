from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import Chapter, Story


class StoryManifestStore:
    """Per-user/per-story chapter index cache; never stores chapter content."""

    schema_version = 1

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
        path = self.path_for(user_id, story.story_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._to_manifest(story)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def _to_manifest(cls, story: Story) -> dict[str, Any]:
        return {
            "schema_version": cls.schema_version,
            "story_id": story.story_id,
            "source_url": story.source_url,
            "site": story.site,
            "title": story.title,
            "author": story.author,
            "chapters": [
                {
                    "number": chapter.number,
                    "title": chapter.title,
                    "url": chapter.url,
                    **({"external_id": chapter.external_id} if getattr(chapter, "external_id", None) else {}),
                }
                for chapter in sorted(story.chapters, key=lambda item: item.number)
            ],
        }

    @staticmethod
    def _from_manifest(data: dict[str, Any]) -> Story:
        chapters = []
        for item in data.get("chapters", []):
            chapters.append(
                Chapter(
                    number=int(item["number"]),
                    title=item.get("title", ""),
                    url=item["url"],
                    external_id=item.get("external_id"),
                )
            )
        chapters.sort(key=lambda item: item.number)
        return Story(
            story_id=data["story_id"],
            source_url=data["source_url"],
            site=data["site"],
            title=data.get("title", ""),
            author=data.get("author", ""),
            chapters=chapters,
            target_chapter_number=chapters[0].number if chapters else None,
        )
