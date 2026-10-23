from pathlib import Path
import pytest
from story_scraper.core.adapter import AdapterNotApplicable, SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.registry import AdapterRegistry
from story_scraper.core.resolution import AdapterResolutionStore

class RejectingAdapter(SiteAdapter):
    name="rejecting"; family="test"; priority=100
    @classmethod
    def matches(cls,url): return True
    def build_index(self,url): raise AdapterNotApplicable("not this site")
    def refresh_tail(self,story): return []
    def fetch_chapter(self,chapter): return "", True

class WorkingAdapter(SiteAdapter):
    name="working"; family="test"; priority=50
    @classmethod
    def matches(cls,url): return True
    def build_index(self,url): return Story("story-1",url,"example.test")
    def refresh_tail(self,story): return []
    def fetch_chapter(self,chapter): return "", True

def test_known_failure_is_fast_and_known_good_is_listed(tmp_path: Path):
    store=AdapterResolutionStore(tmp_path/"resolution.jsonl")
    store.record("bad.test","__registry__","failure","NO_CHAPTER_LINKS")
    store.record("good.test","working","success","RESOLVED")
    assert store.coverage("bad.test").status=="failure"
    assert store.coverage("bad.test").reason=="NO_CHAPTER_LINKS"
    assert store.coverage("good.test").status=="good"
    assert [x.domain for x in store.failure_list()]==["bad.test"]
    assert [x.domain for x in store.known_good_list()]==["good.test"]

def test_known_failure_skips_network_resolution(tmp_path: Path):
    store=AdapterResolutionStore(tmp_path/"resolution.jsonl")
    store.record("example.test","__registry__","failure","HTTP_403")
    registry=AdapterRegistry([WorkingAdapter],resolution_store=store)
    with pytest.raises(AdapterNotApplicable, match="Known unsupported domain"):
        registry.resolve_source("https://example.test/story")
    assert len(store.records())==1

def test_new_success_replaces_active_failure(tmp_path: Path):
    store=AdapterResolutionStore(tmp_path/"resolution.jsonl")
    store.record("example.test","__registry__","failure","UNSUPPORTED_STRUCTURE")
    store.record("example.test","working","success","RESOLVED")
    assert store.known_failure("example.test") is False
    assert store.known_good("example.test") is True
    assert store.failure_list()==[]
