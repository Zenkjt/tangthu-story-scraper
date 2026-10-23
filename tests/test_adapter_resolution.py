from pathlib import Path

import pytest

from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import AdapterResolutionStore


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

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    def build_index(self, url: str) -> Story:
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
    assert all(item.domain == "example.test" for item in records)


def test_resolution_records_real_failure_and_reraises(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    registry = AdapterRegistry([BrokenAdapter], resolution_store=store)

    with pytest.raises(TimeoutError):
        registry.resolve_source("https://example.test/story")

    records = store.records()
    assert len(records) == 1
    assert records[0].adapter == "broken"
    assert records[0].result == "failure"
    assert records[0].reason == "TIMEOUT"


def test_cached_success_is_prioritized(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "adapter-resolution.jsonl")
    store.record("example.test", "working", "success", "RESOLVED")

    registry = AdapterRegistry(
        [RejectingAdapter, WorkingAdapter],
        resolution_store=store,
    )

    candidates = registry.resolve("https://example.test/story")
    assert candidates[0] is WorkingAdapter
