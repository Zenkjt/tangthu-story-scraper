from __future__ import annotations
import hashlib
from .adapter import SiteAdapter
from .epub import EpubSink
from .models import Story, ChapterStatus
from .state import StoryStateStore


class StoryEngine:
    """
    Core rule:
      one trigger == exactly one chapter fetch.

    The engine owns state/selection. The adapter owns website knowledge.
    The EpubSink owns the existing EPUB implementation.
    """

    def __init__(
        self,
        state: StoryStateStore,
        epub: EpubSink,
        adapter: SiteAdapter,
    ):
        self.state = state
        self.epub = epub
        self.adapter = adapter

    def initialize(self, story: Story) -> Story:
        self.state.save(story)
        self.epub.create(story)
        return story

    def next_target(self, story: Story):
        if not story.chapters:
            return None
        if story.current_index >= len(story.chapters):
            return None
        return story.chapters[story.current_index]

    def trigger_next(self, story: Story) -> Story:
        chapter = self.next_target(story)
        if chapter is None:
            # Only refresh the tail when the known queue is exhausted.
            self._refresh_tail(story)
            chapter = self.next_target(story)
            if chapter is None:
                return story

        content, complete = self.adapter.fetch_chapter(chapter)
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # OPEN chapters are re-fetched and replaced on every trigger.
        if chapter.content_hash is None:
            self.epub.append(story, chapter, content)
        elif chapter.content_hash != new_hash:
            self.epub.replace(story, chapter, content)

        chapter.content_hash = new_hash

        if complete:
            chapter.status = ChapterStatus.COMPLETE
            story.current_index = chapter.number
        else:
            chapter.status = ChapterStatus.OPEN

        self.state.save(story)

        # If this was the last known chapter, refresh only the tail.
        if chapter.number == len(story.chapters):
            self._refresh_tail(story)

        self.state.save(story)
        return story

    def trigger_previous(self, story: Story) -> Story:
        if story.current_index <= 1:
            return story
        story.current_index -= 1
        self.state.save(story)
        return story

    def _refresh_tail(self, story: Story) -> None:
        updates = self.adapter.refresh_tail(story)
        known = {c.number: c for c in story.chapters}

        for chapter in updates:
            existing = known.get(chapter.number)
            if existing is None:
                story.chapters.append(chapter)
            else:
                existing.title = chapter.title
                existing.url = chapter.url
                existing.status = chapter.status

        story.chapters.sort(key=lambda c: c.number)
