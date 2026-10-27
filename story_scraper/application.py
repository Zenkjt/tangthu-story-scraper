from __future__ import annotations

from pathlib import Path

from .core.engine import StoryEngine
from .core.epub import EpubSink
from .core.manifest import StoryManifestStore
from .core.models import Story
from .core.registry import AdapterRegistry, ResolvedStorySource, default_registry
from .core.resolution import AdapterResolutionStore
from .core.state import StoryStateStore
from .story_catalog import StoryCatalogEpubSink


class StoryApplication:
    """Application entry point between state, manifest, catalog, and StoryEngine."""

    def __init__(
        self,
        state: StoryStateStore,
        manifest: StoryManifestStore,
        registry: AdapterRegistry | None = None,
        catalog: StoryCatalogEpubSink | None = None,
    ):
        self.state = state
        self.manifest = manifest
        self.registry = registry or default_registry()
        self.catalog = catalog

    def initialize(
        self,
        user_id: str,
        url: str,
        epub: EpubSink,
        *,
        start_toc_index: int | None = None,
        start_chapter_number: int | None = None,
        catalog: StoryCatalogEpubSink | None = None,
    ) -> Story:
        source: ResolvedStorySource = self.registry.resolve_source(url)
        story = source.story
        story.normalize_toc()

        if start_toc_index is not None:
            target = story.entry_at(int(start_toc_index))
            if target is None:
                raise ValueError(f"Unknown TOC position: {start_toc_index}")
            story.target_toc_index = target.toc_index
            story.registered_toc_index = target.toc_index
        elif start_chapter_number is not None:
            target = next(
                (
                    entry
                    for entry in story.chapters
                    if entry.number == int(start_chapter_number)
                ),
                None,
            )
            if target is None:
                raise ValueError(
                    f"Unknown source chapter number: {start_chapter_number}"
                )
            story.target_toc_index = target.toc_index

        self.manifest.save(user_id, story)

        engine = StoryEngine(
            self.state,
            epub,
            source.adapter,
            catalog=catalog or self.catalog,
        )
        story = engine.initialize(story)

        # Only adapters that explicitly opt in fetch during registration.
        # Wattpad chapter URLs opt in; other adapters retain old behavior.
        if source.adapter.fetch_initial_target_on_register(story):
            story = engine.trigger_next(story)
            self.manifest.save(user_id, story)

        return story

    def trigger_next(
        self,
        user_id: str,
        story_id: str,
        epub: EpubSink,
        *,
        catalog: StoryCatalogEpubSink | None = None,
    ) -> Story:
        story = self._load_story(user_id, story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        return_story = StoryEngine(
            self.state,
            epub,
            adapter,
            catalog=catalog or self.catalog,
        ).trigger_next(story)
        self.manifest.save(user_id, return_story)
        return return_story

    def trigger_previous(
        self,
        user_id: str,
        story_id: str,
        epub: EpubSink,
        *,
        catalog: StoryCatalogEpubSink | None = None,
    ) -> Story:
        story = self._load_story(user_id, story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        story = StoryEngine(
            self.state,
            epub,
            adapter,
            catalog=catalog or self.catalog,
        ).trigger_previous(story)
        self.manifest.save(user_id, story)
        return story

    def load_current(self, user_id: str, story_id: str) -> Story:
        return self._load_story(user_id, story_id)

    def set_target(self, user_id: str, story_id: str, toc_index: int) -> Story:
        story = self._load_story(user_id, story_id)
        target = story.entry_at(int(toc_index))
        if target is None:
            raise ValueError(f"Unknown TOC position: {toc_index}")
        story.target_toc_index = target.toc_index
        self.state.save(story)
        return story

    @staticmethod
    def _identity(entry):
        if entry.external_id:
            return ("external_id", entry.external_id)
        url = str(entry.url or "").strip().rstrip("/")
        if url:
            return ("url", url)
        if entry.number is not None:
            return ("number", entry.kind, entry.number)
        return ("fallback", entry.kind, entry.title)

    def _load_story(self, user_id: str, story_id: str) -> Story:
        state_story = self.state.load(story_id)
        if state_story is None:
            raise FileNotFoundError(
                f"No story state found for story_id={story_id!r}"
            )

        manifest_story = self.manifest.load(user_id, story_id)
        if manifest_story is None:
            self.manifest.save(user_id, state_story)
            return state_story

        runtime = {
            self._identity(chapter): chapter
            for chapter in state_story.chapters
        }
        for chapter in manifest_story.chapters:
            old = runtime.get(self._identity(chapter))
            if old is not None:
                chapter.status = old.status
                chapter.content_hash = old.content_hash

        manifest_story.target_toc_index = state_story.target_toc_index
        manifest_story.registered_toc_index = (
            state_story.registered_toc_index
            if state_story.registered_toc_index is not None
            else manifest_story.registered_toc_index
        )
        state_story.chapters = manifest_story.chapters
        state_story.normalize_toc()
        return state_story


def build_application(
    state_root: str | Path,
    manifest_root: str | Path,
    registry: AdapterRegistry | None = None,
    catalog: StoryCatalogEpubSink | None = None,
    resolution_root: str | Path | None = None,
) -> StoryApplication:
    if registry is None:
        resolution_store = (
            AdapterResolutionStore(resolution_root)
            if resolution_root is not None
            else None
        )
        registry = default_registry(resolution_store)

    return StoryApplication(
        StoryStateStore(state_root),
        StoryManifestStore(manifest_root),
        registry,
        catalog,
    )
