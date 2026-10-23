from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BookshelfRegistration:
    path: str
    name: str
    story_id: str | None = None


class BookshelfRegistrationStore:
    """Persist the user's registered receiving folder and current story."""

    filename = ".tangthu-bookshelf.json"

    def load(self, folder: str | Path) -> BookshelfRegistration | None:
        root = Path(folder).expanduser().resolve()
        path = root / self.filename
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return BookshelfRegistration(
            path=str(root),
            name=data.get("name") or root.name,
            story_id=data.get("story_id"),
        )

    def register(self, folder: str | Path) -> BookshelfRegistration:
        root = Path(folder).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        existing = self.load(root)
        registration = BookshelfRegistration(
            path=str(root),
            name=(existing.name if existing else root.name),
            story_id=(existing.story_id if existing else None),
        )
        self._write(root, registration)
        return registration

    def set_story(self, folder: str | Path, story_id: str | None) -> BookshelfRegistration:
        root = Path(folder).expanduser().resolve()
        current = self.register(root)
        updated = BookshelfRegistration(current.path, current.name, story_id)
        self._write(root, updated)
        return updated

    def clear_story(self, folder: str | Path) -> BookshelfRegistration:
        return self.set_story(folder, None)

    def _write(self, root: Path, registration: BookshelfRegistration) -> None:
        path = root / self.filename
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {"name": registration.name, "story_id": registration.story_id},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)
