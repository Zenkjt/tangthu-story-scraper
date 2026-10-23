from pathlib import Path

from story_scraper.application import StoryApplication
from story_scraper.core.manifest import StoryManifestStore
from story_scraper.core.models import Chapter, ChapterStatus, Story
from story_scraper.core.state import StoryStateStore


class FakeAdapter:
    name = "fake"
    build_index_calls = 0

    def build_index(self, url):
        type(self).build_index_calls += 1
        return Story(
            story_id="story-1",
            source_url=url,
            site="fake",
            title="Test Story",
            author="Tester",
            chapters=[
                Chapter(1, "Chapter 1", "https://example.test/ch1"),
                Chapter(2, "Chapter 2", "https://example.test/ch2"),
            ],
        )

    def fetch_chapter(self, chapter):
        return "<p>chapter</p>", True

    def refresh_tail(self, story):
        return []


class FakeRegistry:
    def __init__(self):
        self.adapter = FakeAdapter()

    def resolve_source(self, url):
        return type(
            "Resolved",
            (),
            {"adapter": self.adapter, "story": self.adapter.build_index(url)},
        )()

    def resolve_instance(self, url):
        return self.adapter


class FakeEpub:
    def create(self, story):
        pass

    def append(self, story, chapter, content):
        pass

    def replace(self, story, chapter, content):
        pass


def test_initialize_then_trigger_uses_manifest_without_reindex(tmp_path: Path):
    FakeAdapter.build_index_calls = 0
    app = StoryApplication(
        StoryStateStore(tmp_path / "state"),
        StoryManifestStore(tmp_path / "manifest"),
        FakeRegistry(),
    )
    epub = FakeEpub()

    app.initialize("user-a", "https://example.test/story", epub)
    assert FakeAdapter.build_index_calls == 1

    story = app.trigger_next("user-a", "story-1", epub)

    assert FakeAdapter.build_index_calls == 1
    assert story.target_chapter_number == 2
    assert story.chapters[0].status is ChapterStatus.COMPLETE


def test_manifest_isolated_per_user(tmp_path: Path):
    store = StoryManifestStore(tmp_path / "manifest")
    story = Story(
        story_id="story-1",
        source_url="https://example.test/story",
        site="fake",
        chapters=[Chapter(1, "Chapter 1", "https://example.test/ch1")],
    )

    store.save("user-a", story)

    assert store.load("user-a", "story-1") is not None
    assert store.load("user-b", "story-1") is None
