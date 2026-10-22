from __future__ import annotations

from pathlib import Path

from .core.engine import StoryEngine
from .core.epub import EpubSink
from .core.models import Story
from .core.registry import AdapterRegistry, ResolvedStorySource, default_registry
from .core.state import StoryStateStore


class StoryApplication:
    """Application entry point between URL/state and the StoryEngine."""

    def __init__(
        self,
        state: StoryStateStore,
        registry: AdapterRegistry | None = None,
    ):
        self.state = state
        self.registry = registry or default_registry()

    def initialize(self, url: str, epub: EpubSink) -> Story:
        """Resolve URL, build the index, and initialize the engine with the same adapter."""
        source: ResolvedStorySource = self.registry.resolve_source(url)
        engine = StoryEngine(self.state, epub, source.adapter)
        return engine.initialize(source.story)

    def trigger_next(self, story_id: str, epub: EpubSink) -> Story:
        """Load persisted state and trigger exactly one chapter."""
        story = self._load_story(story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        engine = StoryEngine(self.state, epub, adapter)
        return engine.trigger_next(story)

    def trigger_previous(self, story_id: str, epub: EpubSink) -> Story:
        """Move the target backward without fetching a chapter."""
        story = self._load_story(story_id)
        adapter = self.registry.resolve_instance(story.source_url)
        engine = StoryEngine(self.state, epub, adapter)
        return engine.trigger_previous(story)

    def _load_story(self, story_id: str) -> Story:
        story = self.state.load(story_id)
        if story is None:
            raise FileNotFoundError(
                f"No story state found for story_id={story_id!r}"
            )
        return story


def build_application(
    state_root: str | Path,
    registry: AdapterRegistry | None = None,
) -> StoryApplication:
    """Small factory for future CLI/web/plugin trigger entry points."""
    return StoryApplication(
        state=StoryStateStore(state_root),
        registry=registry,
    )
