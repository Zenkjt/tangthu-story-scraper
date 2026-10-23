from pathlib import Path

from story_scraper.core.adapter import SiteAdapter
from story_scraper.core.models import Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import AdapterResolutionStore


class RegisteredAdapter(SiteAdapter):
    name = "registered"
    family = "test"
    priority = 100

    @classmethod
    def matches(cls, url):
        return "example.test" in url

    def build_index(self, url):
        return Story("story-1", url, "example.test")

    def refresh_tail(self, story):
        return []

    def fetch_chapter(self, chapter):
        return "", True


def test_registration_does_not_require_domain_list():
    registry = AdapterRegistry([RegisteredAdapter])
    assert registry.registered_adapters() == (RegisteredAdapter,)
    assert registry.registered_adapter_names() == ["registered"]


def test_active_coverage_is_derived_from_resolution_history(tmp_path: Path):
    store = AdapterResolutionStore(tmp_path / "resolution.jsonl")
    store.record(
        "old.test", "registered", "failure", "UNSUPPORTED_STRUCTURE",
        url="https://old.test/story",
    )
    store.record(
        "old.test", "registered", "success", "RESOLVED",
        url="https://old.test/story",
    )
    store.record(
        "new.test", "registered", "success", "RESOLVED",
        url="https://new.test/story",
    )

    assert [item.domain for item in store.known_good_list()] == [
        "new.test", "old.test"
    ]
    assert [item.domain for item in store.coverage_for_adapter("registered")] == [
        "new.test", "old.test"
    ]
    assert store.failure_list() == []
