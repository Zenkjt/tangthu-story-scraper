from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit

from .adapter import SiteAdapter
from .epub import EpubSink
from .models import Chapter, ChapterContent, ChapterStatus, Story
from .state import StoryStateStore


class StoryEngine:
    """Fetch one TOC entry and refresh the complete source TOC at its tail."""

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
            changed = self._refresh_full_toc(story)
            entry = self.next_target(story)
            if entry is None:
                if changed and self.catalog is not None:
                    self.catalog.update(story)
                self.state.save(story)
                return story

        before_signature = self._toc_signature(story)
        current_identity = self._identity(entry)

        fetched = self.adapter.fetch_chapter(entry)
        content, complete = fetched

        if isinstance(content, ChapterContent):
            new_hash = content.fingerprint()
        else:
            new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Every fetch produces a brand-new one-entry 0neStory.epub.
        self.epub.append(story, entry, content)

        entry.content_hash = new_hash
        entry.status = ChapterStatus.COMPLETE if complete else ChapterStatus.OPEN

        if complete:
            story.target_toc_index = self._next_known_toc_index(
                story, entry.toc_index
            )
        else:
            story.target_toc_index = entry.toc_index

        catalog_changed = before_signature != self._toc_signature(story)

        # Reaching the last entry known to Tàng Thư is a source refresh point.
        if entry.toc_index == self._last_known_toc_index(story):
            refreshed_changed = self._refresh_full_toc(story)
            catalog_changed = catalog_changed or refreshed_changed

            if complete:
                story.target_toc_index = self._next_after_identity(
                    story, current_identity
                )
            else:
                current = self._find_identity(story, current_identity)
                story.target_toc_index = (
                    current.toc_index if current is not None else None
                )

        if catalog_changed and self.catalog is not None:
            self.catalog.update(story)

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

    def _refresh_full_toc(self, story: Story) -> bool:
        before = self._toc_signature(story)
        old_entries = list(story.chapters)
        old_target = story.entry_at(story.target_toc_index)
        old_registered = story.entry_at(story.registered_toc_index)

        refreshed = self.adapter.refresh_index(story)
        incoming = list(refreshed.chapters)

        by_url = {
            self._url_key(entry.url): entry
            for entry in old_entries
            if self._url_key(entry.url)
        }
        by_external = {
            entry.external_id: entry
            for entry in old_entries
            if entry.external_id
        }
        by_number = {
            (entry.kind, entry.number): entry
            for entry in old_entries
            if entry.number is not None
        }

        merged: list[Chapter] = []
        for new_entry in incoming:
            old = None
            if new_entry.external_id:
                old = by_external.get(new_entry.external_id)
            if old is None:
                old = by_url.get(self._url_key(new_entry.url))
            if old is None and new_entry.number is not None:
                old = by_number.get((new_entry.kind, new_entry.number))

            if old is not None:
                new_entry.status = old.status
                new_entry.content_hash = old.content_hash

            merged.append(new_entry)

        story.chapters = merged
        story.title = refreshed.title or story.title
        story.author = refreshed.author or story.author
        story.index_url = refreshed.index_url or story.index_url
        story.site = refreshed.site or story.site
        # source_url is the original user-supplied registration URL and must
        # not be replaced by the adapter's index URL.
        story.normalize_toc()

        story.target_toc_index = self._index_for_identity(story, old_target)
        story.registered_toc_index = self._index_for_identity(
            story, old_registered
        )

        after = self._toc_signature(story)
        return before != after

    @staticmethod
    def _url_key(url: str) -> str:
        if not url:
            return ""
        parsed = urlsplit(url)
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                parsed.query,
                "",
            )
        )

    @classmethod
    def _identity(cls, entry: Chapter | None):
        if entry is None:
            return None
        if entry.external_id:
            return ("external_id", entry.external_id)
        url = cls._url_key(entry.url)
        if url:
            return ("url", url)
        if entry.number is not None:
            return ("number", entry.kind, entry.number)
        return ("fallback", entry.kind, entry.title)

    @classmethod
    def _find_identity(cls, story: Story, identity):
        if identity is None:
            return None
        return next(
            (entry for entry in story.chapters if cls._identity(entry) == identity),
            None,
        )

    @classmethod
    def _index_for_identity(cls, story: Story, old_entry: Chapter | None):
        if old_entry is None:
            return None
        current = cls._find_identity(story, cls._identity(old_entry))
        return current.toc_index if current is not None else None

    @classmethod
    def _next_after_identity(cls, story: Story, identity):
        current = cls._find_identity(story, identity)
        if current is None:
            return None
        return cls._next_known_toc_index(story, current.toc_index)

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
    def _toc_signature(story: Story):
        return tuple(
            (
                entry.toc_index,
                entry.number,
                entry.title,
                StoryEngine._url_key(entry.url),
                entry.external_id,
                entry.kind,
            )
            for entry in sorted(story.chapters, key=lambda item: item.toc_index)
        )
