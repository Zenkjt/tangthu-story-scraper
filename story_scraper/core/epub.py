from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Chapter, Story


class EpubSink(ABC):
    """Artifact writer used by StoryEngine."""

    @abstractmethod
    def create(self, story: Story) -> None:
        """Create or initialize the EPUB artifact for a story."""
        raise NotImplementedError

    @abstractmethod
    def append(self, story: Story, chapter: Chapter, content: str) -> None:
        """Append a newly fetched chapter to the EPUB artifact."""
        raise NotImplementedError

    @abstractmethod
    def replace(self, story: Story, chapter: Chapter, content: str) -> None:
        """Replace an existing chapter in the EPUB artifact."""
        raise NotImplementedError
