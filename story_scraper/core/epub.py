from __future__ import annotations
from abc import ABC, abstractmethod
from .models import Story, Chapter


class EpubSink(ABC):
    """Adapter around the existing Tàng thư chapter→EPUB downloader."""

    @abstractmethod
    def create(self, story: Story) -> None:
        raise NotImplementedError

    @abstractmethod
    def append(self, story: Story, chapter: Chapter, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def replace(self, story: Story, chapter: Chapter, content: str) -> None:
        raise NotImplementedError
