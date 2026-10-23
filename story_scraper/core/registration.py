from __future__ import annotations

import hashlib
import json
from pathlib import Path


class StoryRegistrationStore:
    """Per-user URL -> story registration index.

    This is only a registration/index layer. Story metadata and runtime state
    remain owned by Story Manifest and Story State respectively.
    """

    schema_version = 1

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def path_for(self, user_id: str) -> Path:
        return self.root / f"{self._key(user_id)}.json"

    def load(self, user_id: str) -> dict[str, str]:
        path = self.path_for(user_id)
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data.get("stories", {}))

    def save(self, user_id: str, stories: dict[str, str]) -> None:
        path = self.path_for(user_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(
                {"schema_version": self.schema_version, "stories": stories},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)

    def get(self, user_id: str, source_url: str) -> str | None:
        return self.load(user_id).get(source_url)

    def register(self, user_id: str, source_url: str, story_id: str) -> str:
        stories = self.load(user_id)
        existing = stories.get(source_url)
        if existing is not None:
            return existing
        stories[source_url] = story_id
        self.save(user_id, stories)
        return story_id
