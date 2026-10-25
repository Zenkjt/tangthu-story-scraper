from __future__ import annotations

import hashlib

from .adapter import SiteAdapter
from .epub import EpubSink
from .models import ChapterContent, ChapterStatus, Story
from .state import StoryStateStore


class StoryEngine:
    """One trigger fetches exactly one ordered TOC entry."""

    def __init__(
        self,
        state: StoryStateStore,
        epub: EpubSink,
        adapter: SiteAdapter,
        catalog=None,
    ):
        self.state = state
        self.epub = epub
        self.adapter = adapter
        self.catalog = catalog

    def initialize(self, story: Story) -> Story:
        story.normalize_toc()
        if story.target_toc_index is None and story.chapters:
            story.target_toc_index = story.chapters[0].toc_index
        self.state.save(story)
        self.epub.create(story)
        if self.catalog is not None:
            self.catalog.create(story)
        return story

    def next_target(self, story: Story):
        return story.entry_at(story.target_toc_index)

    def jump_to_toc(self, story: Story, toc_index: int) -> Story:
        story.normalize_toc()
        target = story.entry_at(int(toc_index))
        if target is None:
            raise ValueError(f"Unknown TOC position: {toc_index}")
        story.target_toc_index = target.toc_index
        self.state.save(story)
        return story

    def trigger_next(self, story: Story) -> Story:
        story.normalize_toc()
        entry = self.next_target(story)

        if entry is None:
            self._refresh_tail(story)
            entry = self.next_target(story)
            if entry is None:
                return story

        fetched = self.adapter.fetch_chapter(entry)
        content, complete = fetched

        if isinstance(content, ChapterContent):
            new_hash = content.fingerprint()
        else:
            new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Every fetch produces a brand-new one-chapter 0neStory.epub.
        self.epub.append(story, entry, content)

        entry.content_hash = new_hash
        entry.status = ChapterStatus.COMPLETE if complete else ChapterStatus.OPEN

        if complete:
            story.target_toc_index = self._next_known_toc_index(
                story, entry.toc_index
            )
        else:
            story.target_toc_index = entry.toc_index

        if entry.toc_index == self._last_known_toc_index(story):
            before = self._toc_signature(story)
            self._refresh_tail(story)
            after = self._toc_signature(story)

            if self.catalog is not None and before != after:
                self.catalog.update(story)

            if complete:
                story.target_toc_index = self._next_known_toc_index(
                    story, entry.toc_index
                )

        self.state.save(story)
        return story

    def trigger_previous(self, story: Story) -> Story:
        if not story.chapters:
            return story

        story.normalize_toc()
        if story.target_toc_index is None:
            story.target_toc_index = story.chapters[-1].toc_index
        else:
            previous = [
                entry.toc_index
                for entry in story.chapters
                if entry.toc_index < story.target_toc_index
            ]
            if previous:
                story.target_toc_index = previous[-1]

        self.state.save(story)
        return story

    @staticmethod
    def _next_known_toc_index(story: Story, toc_index: int) -> int | None:
        following = [
            entry.toc_index
            for entry in story.chapters
            if entry.toc_index > toc_index
        ]
        return min(following) if following else None

    @staticmethod
    def _last_known_toc_index(story: Story) -> int | None:
        return max((entry.toc_index for entry in story.chapters), default=None)

    @staticmethod
    def _toc_signature(story: Story) -> tuple[tuple[int, str, str, str], ...]:
        return tuple(
            (entry.toc_index, entry.title, entry.url, entry.kind)
            for entry in sorted(story.chapters, key=lambda item: item.toc_index)
        )

    def _refresh_tail(self, story: Story) -> None:
        updates = self.adapter.refresh_tail(story)
        known_urls = {entry.url.rstrip("/") for entry in story.chapters}
        next_index = max(
            (entry.toc_index for entry in story.chapters),
            default=0,
        ) + 1

        for incoming in updates:
            if incoming.url.rstrip("/") in known_urls:
                continue
            incoming.toc_index = next_index
            next_index += 1
            story.chapters.append(incoming)
            known_urls.add(incoming.url.rstrip("/"))

        story.normalize_toc()
