from __future__ import annotations

from pathlib import Path

from .core.engine import StoryEngine
from .core.epub import EpubSink
from .core.manifest import StoryManifestStore
from .core.models import Story
from .core.registry import AdapterRegistry, ResolvedStorySource, default_registry
from .core.state import StoryStateStore


class StoryApplication:
    """Application entry point between user/story state, manifest, and StoryEngine."""

    def __init__(
        self,
        state: StoryStateStore,
        manifest: StoryManifestStore,
        registry: AdapterRegistry | None = None,
    ):
        self.state = state
        self.manifest = manifest
        self.registry = registry or default_registry()

    def initialize(self, user_id: str, url: str, epub: EpubSink) -> Story:
        source: ResolvedStorySource = self.registry.resolve_source(url)
        story = source.story
        self.manifest.save(user_id, story)
        engine = StoryEngine(self.state, epub, source.adapter)
        return engine.initialize(story)

    def trigger_next(self, user_id: str, story_id: str, epub: EpubSink) -> Story:
        story = self._load_story(user_id, story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        story = StoryEngine(self.state, epub, adapter).trigger_next(story)
        self.manifest.save(user_id, story)
        return story

    def trigger_previous(self, user_id: str, story_id: str, epub: EpubSink) -> Story:
        story = self._load_story(user_id, story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        story = StoryEngine(self.state, epub, adapter).trigger_previous(story)
        self.manifest.save(user_id, story)
        return story

    def _load_story(self, user_id: str, story_id: str) -> Story:
        state_story = self.state.load(story_id)
        if state_story is None:
            raise FileNotFoundError(f"No story state found for story_id={story_id!r}")

        manifest_story = self.manifest.load(user_id, story_id)
        if manifest_story is None:
            # Migration: old state already contains the chapter index.
            self.manifest.save(user_id, state_story)
            return state_story

        runtime = {c.number: c for c in state_story.chapters}
        for chapter in manifest_story.chapters:
            old = runtime.get(chapter.number)
            if old is not None:
                chapter.status = old.status
                chapter.content_hash = old.content_hash

        state_story.chapters = manifest_story.chapters
        return state_story


def build_application(
    state_root: str | Path,
    manifest_root: str | Path,
    registry: AdapterRegistry | None = None,
) -> StoryApplication:
    return StoryApplication(
        state=StoryStateStore(state_root),
        manifest=StoryManifestStore(manifest_root),
        registry=registry,
    )
