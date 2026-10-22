from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Chapter, ChapterContent, Story


class EpubSink(ABC):
    """Artifact writer used by StoryEngine."""

    @abstractmethod
    def create(self, story: Story) -> None:
        raise NotImplementedError

    @abstractmethod
    def append(self, story: Story, chapter: Chapter, content: str | ChapterContent) -> None:
        raise NotImplementedError

    @abstractmethod
    def replace(self, story: Story, chapter: Chapter, content: str | ChapterContent) -> None:
        raise NotImplementedError
