"""Boundary for the persistent Story cache.

The cache contains navigation/metadata only. Chapter content is never persisted here.
GitHub credentials belong to the Worker, not to the scraper domain.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoryCacheKey:
    user_id: str
    story_id: str


class StoryCacheStore(Protocol):
    def load(self, key: StoryCacheKey) -> dict | None:
        ...

    def save(self, key: StoryCacheKey, data: dict) -> None:
        ...

    def cover_url(self, key: StoryCacheKey) -> str | None:
        ...

    def save_cover(self, key: StoryCacheKey, content: bytes, media_type: str) -> str:
        ...
