from pathlib import Path

from story_scraper.application import StoryApplication
from story_scraper.core.manifest import StoryManifestStore
from story_scraper.core.models import Chapter, Story
from story_scraper.core.state import StoryStateStore


class FakeAdapter:
    name = "fake"

    def build_index(self, url):
        return Story(
            story_id="story-1",
            source_url=url,
            site="fake",
            title="Test Story",
            chapters=[
                Chapter(1, "Chapter 1", "https://example.test/ch1"),
                Chapter(2, "Chapter 2", "https://example.test/ch2"),
            ],
        )


class FakeRegistry:
    def __init__(self):
        self.adapter = FakeAdapter()

    def resolve_source(self, url):
        return type("Resolved", (), {"adapter": self.adapter, "story": self.adapter.build_index(url)})()

    def resolve_instance(self, url):
        return self.adapter


class FakeEpub:
    def create(self, story):
        pass

    def append(self, story, chapter, content):
        pass

    def replace(self, story, chapter, content):
        pass


def test_initialize_can_start_at_arbitrary_chapter(tmp_path: Path):
    app = StoryApplication(
        StoryStateStore(tmp_path / "state"),
        StoryManifestStore(tmp_path / "manifest"),
        FakeRegistry(),
    )

    story = app.initialize(
        "local-user",
        "https://example.test/story/chapter-2",
        FakeEpub(),
        start_chapter_number=2,
    )

    assert story.target_chapter_number == 2
