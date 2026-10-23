from pathlib import Path

import pytest

from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import (
    AdapterResolutionStore,
    KnownResolutionFailure,
)


class RejectingAdapter(SiteAdapter):
    name = "rejecting"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    def build_index(self, url: str) -> Story:
        raise AdapterNotApplicable("not this site")

    def refresh_tail(self, story: Story) -> list[Chapter]:
        return []

    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        return "", True


class WorkingAdapter(SiteAdapter):
    name = "working"
    family = "test"
    priority = 50
    calls = 0

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    def build_index(self, url: str) -> Story:
        type(self).calls += 1
        return Story("story-1", url, "example.test")

    def refresh_tail(self, story: Story) -> list[Chapter]:
        return []

    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        return "", True


class BrokenAdapter(SiteAdapter):
    name = "broken"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    def build_index(self, url: str) -> Story:
        raise TimeoutError("request timed out")

    def refresh_tail(self, story: Story) -> list[Chapter]:
        return []

    def fetch_chapter(self, chapter: Chapter) -> tuple[str, bool]:
        return "", True


def test_resolution_records_rejection_and_success(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    registry = AdapterRegistry(
        [RejectingAdapter, WorkingAdapter],
        resolution_store=store,
    )

    source = registry.resolve_source("https://example.test/story")

    assert source.adapter.name == "working"
    records = store.records()
    assert [(item.adapter, item.result, item.reason) for item in records] == [
        ("rejecting", "failure", "ADAPTER_NOT_APPLICABLE"),
        ("working", "success", "RESOLVED"),
    ]


def test_resolution_records_real_failure_and_reraises(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    registry = AdapterRegistry([BrokenAdapter], resolution_store=store)

    with pytest.raises(TimeoutError):
        registry.resolve_source("https://example.test/story")

    records = store.records()
    assert records[0].reason == "TIMEOUT"


def test_known_failure_is_fast_and_does_not_call_adapter(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    store.record(
        "example.test",
        "rejecting",
        "failure",
        "NO_CHAPTER_LINKS",
    )
    WorkingAdapter.calls = 0

    registry = AdapterRegistry(
        [RejectingAdapter],
        resolution_store=store,
    )

    with pytest.raises(KnownResolutionFailure, match="NO_CHAPTER_LINKS"):
        registry.resolve_source("https://example.test/story")

    assert WorkingAdapter.calls == 0


def test_new_matching_adapter_rechecks_known_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    store.record(
        "example.test",
        "old-adapter",
        "failure",
        "NO_CHAPTER_LINKS",
    )

    registry = AdapterRegistry(
        [RejectingAdapter, WorkingAdapter],
        resolution_store=store,
    )

    source = registry.resolve_source("https://example.test/story")
    assert source.adapter.name == "working"


def test_coverage_splits_known_good_and_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    store.record("good.test", "wattpad", "success", "RESOLVED")
    store.record("bad.test", "vnthuquan", "failure", "HTTP_403")

    assert set(store.known_good()) == {"good.test"}
    assert set(store.known_failures()) == {"bad.test"}

    coverage = store.coverage()
    assert coverage["good.test"]["status"] == "known_good"
    assert coverage["bad.test"]["status"] == "known_failure"
    assert coverage["bad.test"]["reason"] == "HTTP_403"


def test_force_recheck_bypasses_known_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    store.record("example.test", "rejecting", "failure", "HTTP_403")

    registry = AdapterRegistry(
        [WorkingAdapter],
        resolution_store=store,
    )

    source = registry.resolve_source(
        "https://example.test/story",
        force_recheck=True,
    )
    assert source.adapter.name == "working"


def test_no_matching_adapter_becomes_fast_known_failure(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    registry = AdapterRegistry([], resolution_store=store)

    with pytest.raises(AdapterNotApplicable):
        registry.resolve_source("https://unknown.test/story")

    with pytest.raises(KnownResolutionFailure, match="NO_MATCHING_ADAPTER"):
        registry.resolve_source("https://unknown.test/story")
