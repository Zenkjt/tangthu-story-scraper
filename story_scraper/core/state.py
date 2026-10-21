from __future__ import annotations
import json
from pathlib import Path
from .models import Story


class StoryStateStore:
    """Small JSON state store. EPUB remains an output artifact, not the state DB."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, story_id: str) -> Path:
        return self.root / f"{story_id}.json"

    def load(self, story_id: str) -> Story | None:
        path = self.path_for(story_id)
        if not path.exists():
            return None
        return Story.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, story: Story) -> None:
        path = self.path_for(story.story_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(story.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
