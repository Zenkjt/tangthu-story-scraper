from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class BookshelfRegistration:
    """Registered Tàng Thư receiving shelf.

    This object contains only registration metadata. It never persists state
    inside the user's Google Drive folder.
    """

    folder_id: str
    name: str
    folder_url: str = ""
    can_edit: bool | None = None


class BookshelfBackend:
    """Interface to the existing Tàng Thư bookshelf-registration service."""

    def inspect(self, folder_url: str) -> BookshelfRegistration | None:
        raise NotImplementedError

    def write(self, registration: BookshelfRegistration, filename: str, payload: bytes) -> None:
        raise NotImplementedError

    def delete_story_files(self, registration: BookshelfRegistration) -> None:
        raise NotImplementedError


def parse_drive_folder_id(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    try:
        parsed = urlparse(raw)
        match = parsed.path.rstrip("/").split("/folders/")
        if len(match) == 2 and match[1]:
            return match[1].split("/")[0]

        query_id = parse_qs(parsed.query).get("id", [""])[0]
        if query_id:
            return query_id
    except ValueError:
        pass

    if raw.replace("-", "").replace("_", "").isalnum() and len(raw) >= 10:
        return raw
    return ""
