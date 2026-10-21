from __future__ import annotations

import hashlib

from .adapter import SiteAdapter
from .epub import EpubSink
from .models import ChapterStatus, Story
from .state import StoryStateStore


class StoryEngine:
    """One trigger fetches exactly one chapter."""

    def __init__(self, state: StoryStateStore, epub: EpubSink, adapter: SiteAdapter):
        self.state = state
        self.epub = epub
        self.adapter = adapter

    def initialize(self, story: Story) -> Story:
        story.chapters.sort(key=lambda c: c.number)
        if story.target_chapter_number is None and story.chapters:
            story.target_chapter_number = story.chapters[0].number
        self.state.save(story)
        self.epub.create(story)
        return story

    def next_target(self, story: Story):
        if story.target_chapter_number is None:
            return None
        return next((c for c in story.chapters
                     if c.number == story.target_chapter_number), None)

    def trigger_next(self, story: Story) -> Story:
        chapter = self.next_target(story)

        if chapter is None:
            self._refresh_tail(story)
            chapter = self.next_target(story)
            if chapter is None:
                return story

        content, complete = self.adapter.fetch_chapter(chapter)
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if chapter.content_hash is None:
            self.epub.append(story, chapter, content)
        elif chapter.content_hash != new_hash:
            self.epub.replace(story, chapter, content)

        chapter.content_hash = new_hash
        chapter.status = ChapterStatus.COMPLETE if complete else ChapterStatus.OPEN

        if complete:
            story.target_chapter_number = self._next_known_number(story, chapter.number)
        else:
            story.target_chapter_number = chapter.number

        if chapter.number == self._last_known_number(story):
            self._refresh_tail(story)
            if complete:
                story.target_chapter_number = self._next_known_number(story, chapter.number)

        self.state.save(story)
        return story

    def trigger_previous(self, story: Story) -> Story:
        if not story.chapters:
            return story

        story.chapters.sort(key=lambda c: c.number)
        if story.target_chapter_number is None:
            story.target_chapter_number = story.chapters[-1].number
        else:
            previous = [c.number for c in story.chapters
                        if c.number < story.target_chapter_number]
            if previous:
                story.target_chapter_number = previous[-1]

        self.state.save(story)
        return story

    @staticmethod
    def _next_known_number(story: Story, number: int) -> int | None:
        following = [c.number for c in story.chapters if c.number > number]
        return min(following) if following else None

    @staticmethod
    def _last_known_number(story: Story) -> int | None:
        return max((c.number for c in story.chapters), default=None)

    def _refresh_tail(self, story: Story) -> None:
        updates = self.adapter.refresh_tail(story)
        by_number = {c.number: c for c in story.chapters}

        for incoming in updates:
            existing = by_number.get(incoming.number)
            if existing is None:
                story.chapters.append(incoming)
            else:
                existing.title = incoming.title or existing.title
                existing.url = incoming.url or existing.url
                # Preserve existing status and content_hash.

        story.chapters.sort(key=lambda c: c.number)
