from __future__ import annotations

import pytest

from story_scraper.adapters.platforms.static_html import StaticHTMLFamilyAdapter
from story_scraper.adapters.platforms.wattpad import WattpadAdapter
from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.registry import AdapterRegistry, default_registry


class ExactAdapter(SiteAdapter):
    name = "exact"
    family = "exact"
    priority = 100

    @classmethod
    def matches(cls, url: str) -> bool:
        return "example.test" in url

    def build_index(self, url: str) -> Story:
        return Story("exact", url, self.name)

    def refresh_tail(self, story: Story) -> list[Chapter]:
        return []

    def fetch_chapter(self, chapter: Chapter):
        return "", True


class FamilyAdapter(SiteAdapter):
    name = "family"
    family = "family"
    priority = 50

    @classmethod
    def matches(cls, url: str) -> bool:
        return "example.test" in url

    def build_index(self, url: str) -> Story:
        return Story("family", url, self.name)

    def refresh_tail(self, story: Story) -> list[Chapter]:
        return []

    def fetch_chapter(self, chapter: Chapter):
        return "", True


class RejectingExactAdapter(ExactAdapter):
    name = "rejecting-exact"

    def build_index(self, url: str) -> Story:
        raise AdapterNotApplicable("not applicable")


class ExplodingExactAdapter(ExactAdapter):
    name = "exploding-exact"

    def build_index(self, url: str) -> Story:
        raise RuntimeError("real parser failure")


def test_registry_prioritizes_exact_adapter():
    registry = AdapterRegistry([FamilyAdapter, ExactAdapter])
    candidates = registry.candidates("https://example.test/story")
    assert [candidate.adapter for candidate in candidates] == [
        ExactAdapter,
        FamilyAdapter,
    ]


def test_registry_falls_back_after_explicit_rejection():
    registry = AdapterRegistry([RejectingExactAdapter, FamilyAdapter])
    source = registry.resolve_source("https://example.test/story")
    assert isinstance(source.adapter, FamilyAdapter)
    assert source.story.site == "family"


def test_real_errors_do_not_trigger_fallback():
    registry = AdapterRegistry([ExplodingExactAdapter, FamilyAdapter])
    with pytest.raises(RuntimeError, match="real parser failure"):
        registry.resolve_source("https://example.test/story")


def test_default_registry_recognizes_current_platforms():
    registry = default_registry()
    assert WattpadAdapter in registry.resolve(
        "https://www.wattpad.com/story/123-example"
    )
    assert StaticHTMLFamilyAdapter in registry.resolve(
        "https://example.com/story"
    )


def test_default_registry_keeps_exact_platform_ahead_of_static_family():
    registry = default_registry()
    candidates = registry.candidates(
        "https://www.wattpad.com/story/123-example"
    )
    assert candidates[0].adapter is WattpadAdapter
    assert all(candidate.priority >= 50 for candidate in candidates)


def test_resolve_instance_returns_implemented_wattpad_adapter():
    registry = default_registry()
    adapter = registry.resolve_instance(
        "https://www.wattpad.com/story/123-example"
    )
    assert isinstance(adapter, WattpadAdapter)


def test_resolve_source_keeps_same_adapter_instance_for_engine():
    class TrackingAdapter(ExactAdapter):
        name = "tracking"

        def build_index(self, url: str) -> Story:
            return Story("tracking", url, self.name)

    registry = AdapterRegistry([TrackingAdapter])
    source = registry.resolve_source("https://example.test/story")
    assert isinstance(source.adapter, TrackingAdapter)
    assert source.story.site == "tracking"
