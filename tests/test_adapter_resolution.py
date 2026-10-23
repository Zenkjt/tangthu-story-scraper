from pathlib import Path

import pytest

from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import AdapterResolutionStore


class RejectingAdapter(SiteAdapter):
    name = "rejecting"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url):
        return True

    def build_index(self, url):
        raise AdapterNotApplicable("not this site")

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


class WorkingAdapter(SiteAdapter):
    name = "working"
    family = "test"
    priority = 50

    @classmethod
    def matches(cls, url):
        return True

    def build_index(self, url):
        return Story("story-1", url, "example.test")

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


class FailingAdapter(SiteAdapter):
    name = "failing"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url):
        return True

    def build_index(self, url):
        raise TimeoutError("network timeout")

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


class OtherAdapter(SiteAdapter):
    name = "other"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url):
        return True

    def build_index(self, url):
        return Story("other-story", url, "example.test")

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


# Phase 4: rejection + success are both recorded.
def test_rejection_and_success_are_recorded(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    registry = AdapterRegistry(
        [RejectingAdapter, WorkingAdapter],
        resolution_store=store,
    )

    source = registry.resolve_source("https://example.test/story")

    assert source.adapter.name == "working"
    records = store.records()
    assert [(r.adapter, r.result, r.reason) for r in records] == [
        ("rejecting", "failure", "ADAPTER_NOT_APPLICABLE"),
        ("working", "success", "RESOLVED"),
    ]


# Phase 4: real adapter failures are recorded and re-raised.
def test_real_failure_is_recorded_and_reraised(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    registry = AdapterRegistry(
        [FailingAdapter],
        resolution_store=store,
    )

    with pytest.raises(TimeoutError, match="network timeout"):
        registry.resolve_source("https://example.test/story")

    records = store.records()
    assert len(records) == 1
    assert records[0].adapter == "failing"
    assert records[0].result == "failure"
    assert records[0].reason == "TIMEOUT"


# Phase 4: a cached successful adapter is prioritized.
def test_cached_successful_adapter_is_prioritized(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "working", "success", "RESOLVED")

    registry = AdapterRegistry(
        [OtherAdapter, WorkingAdapter],
        resolution_store=store,
    )

    assert [adapter.name for adapter in registry.resolve("https://example.test/story")] == [
        "working",
        "other",
    ]


# Phase 5: coverage lists expose the active Known Good / Known Failure state.
def test_known_failure_is_fast_and_known_good_is_listed(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("bad.test", "__registry__", "failure", "NO_CHAPTER_LINKS")
    store.record("good.test", "working", "success", "RESOLVED")

    assert store.coverage("bad.test").status == "failure"
    assert store.coverage("bad.test").reason == "NO_CHAPTER_LINKS"
    assert store.coverage("good.test").status == "good"
    assert [x.domain for x in store.failure_list()] == ["bad.test"]
    assert [x.domain for x in store.known_good_list()] == ["good.test"]


# Phase 5: a known failure must skip adapter/network resolution.
def test_known_failure_skips_network_resolution(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "__registry__", "failure", "HTTP_403")

    registry = AdapterRegistry(
        [WorkingAdapter],
        resolution_store=store,
    )

    with pytest.raises(AdapterNotApplicable, match="Known unsupported domain"):
        registry.resolve_source("https://example.test/story")

    assert len(store.records()) == 1


# Phase 5: a later success becomes the active state while old failure remains historical.
def test_new_success_replaces_active_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record(
        "example.test",
        "__registry__",
        "failure",
        "UNSUPPORTED_STRUCTURE",
    )
    store.record("example.test", "working", "success", "RESOLVED")

    assert store.known_failure("example.test") is False
    assert store.known_good("example.test") is True
    assert store.failure_list() == []
    assert len(store.records()) == 2
