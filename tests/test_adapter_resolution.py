from pathlib import Path

import pytest

from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import AdapterResolutionStore


class RejectingAdapter(SiteAdapter):
    name = "rejecting"; family = "test"; priority = 100
    @classmethod
    def matches(cls, url): return True
    def build_index(self, url): raise AdapterNotApplicable("not this site")
    def refresh_tail(self, story): return []
    def fetch_chapter(self, chapter): return "", True


class WorkingAdapter(SiteAdapter):
    name = "working"; family = "test"; priority = 50
    @classmethod
    def matches(cls, url): return True
    def build_index(self, url): return Story("story-1", url, "example.test")
    def refresh_tail(self, story): return []
    def fetch_chapter(self, chapter): return "", True


class FailingAdapter(SiteAdapter):
    name = "failing"; family = "test"; priority = 100
    @classmethod
    def matches(cls, url): return True
    def build_index(self, url): raise TimeoutError("network timeout")
    def refresh_tail(self, story): return []
    def fetch_chapter(self, chapter): return "", True


class OtherAdapter(SiteAdapter):
    name = "other"; family = "test"; priority = 100
    @classmethod
    def matches(cls, url): return True
    def build_index(self, url): return Story("other-story", url, "example.test")
    def refresh_tail(self, story): return []
    def fetch_chapter(self, chapter): return "", True


def test_rejection_and_success_are_recorded(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    registry = AdapterRegistry([RejectingAdapter, WorkingAdapter], resolution_store=store)
    source = registry.resolve_source("https://example.test/story")
    assert source.adapter.name == "working"
    records = store.records()
    assert [(r.adapter, r.result, r.reason, r.url) for r in records] == [
        ("rejecting", "failure", "ADAPTER_NOT_APPLICABLE", "https://example.test/story"),
        ("working", "success", "RESOLVED", "https://example.test/story"),
    ]


def test_real_failure_is_recorded_and_reraised(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    registry = AdapterRegistry([FailingAdapter], resolution_store=store)
    with pytest.raises(TimeoutError, match="network timeout"):
        registry.resolve_source("https://example.test/story")
    records = store.records()
    assert len(records) == 1
    assert records[0].reason == "TIMEOUT"
    assert records[0].url == "https://example.test/story"


def test_cached_successful_adapter_is_prioritized(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "working", "success", "RESOLVED")
    registry = AdapterRegistry([OtherAdapter, WorkingAdapter], resolution_store=store)
    assert [adapter.name for adapter in registry.resolve("https://example.test/story")] == ["working", "other"]


def test_known_failure_is_fast_and_known_good_is_listed(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("bad.test", "__registry__", "failure", "NO_CHAPTER_LINKS", url="https://bad.test/story")
    store.record("good.test", "working", "success", "RESOLVED", url="https://good.test/story")
    assert store.coverage("bad.test").status == "failure"
    assert store.coverage("bad.test").url == "https://bad.test/story"
    assert [x.domain for x in store.failure_list()] == ["bad.test"]
    assert [x.domain for x in store.known_good_list()] == ["good.test"]


def test_known_failure_skips_network_resolution(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "__registry__", "failure", "HTTP_403", url="https://example.test/story")
    registry = AdapterRegistry([WorkingAdapter], resolution_store=store)
    with pytest.raises(AdapterNotApplicable, match="Known unsupported domain"):
        registry.resolve_source("https://example.test/story")
    assert len(store.records()) == 1


def test_recheck_bypasses_known_failure_and_records_success(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "__registry__", "failure", "UNSUPPORTED_STRUCTURE", url="https://example.test/story")
    registry = AdapterRegistry([WorkingAdapter], resolution_store=store)
    source = registry.recheck_source("https://example.test/story")
    assert source.adapter.name == "working"
    assert store.known_failure("example.test") is False
    assert store.known_good("example.test") is True
    assert len(store.records()) == 2


def test_recheck_failure_stays_in_active_failure_list(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "__registry__", "failure", "UNSUPPORTED_STRUCTURE", url="https://example.test/story")
    registry = AdapterRegistry([RejectingAdapter], resolution_store=store)
    with pytest.raises(AdapterNotApplicable):
        registry.recheck_source("https://example.test/story")
    assert store.known_failure("example.test") is True
    assert store.failure_list()[0].url == "https://example.test/story"


def test_new_success_replaces_active_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record("example.test", "__registry__", "failure", "UNSUPPORTED_STRUCTURE", url="https://example.test/story")
    store.record("example.test", "working", "success", "RESOLVED", url="https://example.test/story")
    assert store.known_failure("example.test") is False
    assert store.known_good("example.test") is True
    assert store.failure_list() == []
    assert len(store.records()) == 2
