from __future__ import annotations

"""Shelf-local Story cache for Tàng Thư.

Persistent data lives in the user's Google Drive shelf, not in GitHub.
The worker uses direct paths only; there is deliberately no list/scan/TTL/GC API.
"""

import base64
import json
import os
import re
from typing import Any

from story_scraper.core.models import ChapterContent, ChapterAsset

CACHE_FOLDER_NAME = "ZtangthuCache"
STATE_FILENAME = "StoryState"
CACHE_SCHEMA_VERSION = 1


class ShelfCacheError(RuntimeError):
    pass


def _post(operation: str, **payload: Any) -> dict[str, Any]:
    from urllib.request import Request, urlopen

    body = {
        "action": "story_cache",
        "operation": operation,
        "token": os.environ["TANGTHU_UPLOAD_TOKEN"],
        **payload,
    }
    request = Request(
        os.environ["TANGTHU_APPS_SCRIPT_URL"],
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise ShelfCacheError(result.get("error", "Story cache operation failed."))
    return result


def _safe_component(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or ""))
    value = value.strip("._")
    if not value or value in {".", ".."}:
        raise ShelfCacheError("Invalid cache path component.")
    return value


def story_id_component(story_id: str) -> str:
    return _safe_component(story_id)


def entry_path(story_id: str, toc_index: int) -> str:
    if int(toc_index) < 1:
        raise ShelfCacheError("TOC index must be >= 1.")
    return (
        f"{CACHE_FOLDER_NAME}/{story_id_component(story_id)}/"
        f"entry_{int(toc_index):03d}.json"
    )


def ensure_story_cache(folder_id: str, story_id: str) -> None:
    _post(
        "ensure",
        folder_id=str(folder_id),
        story_id=story_id_component(story_id),
    )


def write_file(folder_id: str, relative_path: str, payload: bytes, mime_type: str) -> None:
    _post(
        "write",
        folder_id=str(folder_id),
        relative_path=relative_path,
        mime_type=mime_type,
        content_base64=base64.b64encode(payload).decode("ascii"),
    )


def read_file(folder_id: str, relative_path: str) -> bytes | None:
    result = _post(
        "read",
        folder_id=str(folder_id),
        relative_path=relative_path,
    )
    if not result.get("exists"):
        return None
    return base64.b64decode(str(result.get("content_base64") or ""))


def write_story_state(folder_id: str, story: Any) -> None:
    data = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "story_id": story.story_id,
        "reading_entry": story.current_toc_index,
        "target_entry": story.target_toc_index,
        "registered_entry": story.registered_toc_index,
        "story": story.as_dict(),
    }
    write_file(
        folder_id,
        STATE_FILENAME,
        json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        "application/json",
    )


def read_story_state(folder_id: str, story_id: str | None = None) -> dict[str, Any] | None:
    payload = read_file(folder_id, STATE_FILENAME)
    if payload is None:
        return None
    data = json.loads(payload.decode("utf-8"))
    if int(data.get("schema_version", 0)) != CACHE_SCHEMA_VERSION:
        raise ShelfCacheError("Unsupported StoryState schema.")
    if story_id is not None and str(data.get("story_id")) != str(story_id):
        raise ShelfCacheError(
            f"StoryState belongs to {data.get('story_id')!r}, not {story_id!r}."
        )
    return data


def _serialize_content(content: str | ChapterContent) -> dict[str, Any]:
    if isinstance(content, ChapterContent):
        return {
            "type": "chapter_content",
            "html": content.html,
            "assets": [
                {
                    "path": asset.path,
                    "media_type": asset.media_type,
                    "content_base64": base64.b64encode(asset.content).decode("ascii"),
                }
                for asset in content.assets
            ],
        }
    return {"type": "text", "text": str(content)}


def _deserialize_content(data: dict[str, Any]) -> str | ChapterContent:
    if data.get("type") == "chapter_content":
        assets = [
            ChapterAsset(
                path=str(item["path"]),
                content=base64.b64decode(str(item["content_base64"])),
                media_type=str(item["media_type"]),
            )
            for item in data.get("assets", [])
        ]
        return ChapterContent(html=str(data.get("html", "")), assets=assets)
    return str(data.get("text", ""))


def write_entry(folder_id: str, story_id: str, entry: Any, content: str | ChapterContent, complete: bool) -> None:
    toc_index = int(entry.toc_index)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "story_id": story_id,
        "toc_index": toc_index,
        "complete": bool(complete),
        "content": _serialize_content(content),
        "entry": {
            "number": entry.number,
            "title": entry.title,
            "url": entry.url,
            "external_id": entry.external_id,
            "kind": entry.kind,
        },
    }
    write_file(
        folder_id,
        entry_path(story_id, toc_index),
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        "application/json",
    )


def read_complete_entry(folder_id: str, story_id: str, entry: Any) -> tuple[str | ChapterContent, bool] | None:
    payload = read_file(folder_id, entry_path(story_id, int(entry.toc_index)))
    if payload is None:
        return None
    data = json.loads(payload.decode("utf-8"))
    if int(data.get("schema_version", 0)) != CACHE_SCHEMA_VERSION:
        raise ShelfCacheError("Unsupported Story cache entry schema.")
    if str(data.get("story_id")) != str(story_id):
        raise ShelfCacheError("Story cache entry has the wrong story_id.")
    if int(data.get("toc_index", 0)) != int(entry.toc_index):
        raise ShelfCacheError("Story cache entry has the wrong TOC index.")
    if not bool(data.get("complete")):
        return None
    return _deserialize_content(dict(data.get("content") or {})), True


class ShelfCachedAdapter:
    """Wrap one adapter and cache only completed fetched entries on the shelf."""

    def __init__(self, adapter: Any, folder_id: str, story_id: str):
        self._adapter = adapter
        self._folder_id = str(folder_id)
        self._story_id = str(story_id)
        self._ready = False

    def _ensure(self) -> None:
        if not self._ready:
            ensure_story_cache(self._folder_id, self._story_id)
            self._ready = True

    def __getattr__(self, name: str) -> Any:
        return getattr(self._adapter, name)

    def fetch_chapter(self, entry: Any):
        self._ensure()

        # OPEN/PENDING entries are intentionally fetched again. Only a
        # completed entry may be served from persistent cache.
        status = getattr(getattr(entry, "status", None), "value", None)
        if status == "complete":
            cached = read_complete_entry(self._folder_id, self._story_id, entry)
            if cached is not None:
                return cached

        content, complete = self._adapter.fetch_chapter(entry)
        write_entry(
            self._folder_id,
            self._story_id,
            entry,
            content,
            bool(complete),
        )
        return content, complete
