from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.core.adapter import SiteAdapter
from story_scraper.core.models import Chapter, Story
from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore
from story_scraper.story_epub import StoryEpubSink


class FakeOpenTailAdapter(SiteAdapter):
    name = "fake-open-tail"
    family = "test"

    def __init__(self):
        self.fetch_calls = 0
        self.refresh_calls = 0

    @classmethod
    def matches(cls, url: str) -> bool:
        return url.startswith("https://example.com/")

    def build_index(self, url: str) -> Story:
        return Story(
            "open-tail-1",
            url,
            self.name,
            "Open Tail Test",
            "Tester",
            [Chapter(1, "Chapter 1", url + "/1")],
            1,
        )

    def refresh_tail(self, story: Story) -> list[Chapter]:
        self.refresh_calls += 1
        if self.fetch_calls >= 3:
            return [Chapter(2, "Chapter 2", story.source_url + "/2")]
        return []

    def fetch_chapter(self, chapter: Chapter):
        self.fetch_calls += 1
        if chapter.number == 1:
            if self.fetch_calls == 1:
                return "<p>Chapter 1 version 1</p>", False
            if self.fetch_calls == 2:
                return "<p>Chapter 1 version 2</p>", False
            return "<p>Chapter 1 version 2</p>", True
        return "<p>Chapter 2</p>", True


def make_cover(path: Path) -> None:
    Image.new("L", (480, 800), 255).save(path, format="BMP")


def test_open_refetch_replace_and_tail_reindex(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    make_cover(cover)

    adapter = FakeOpenTailAdapter()
    story = adapter.build_index("https://example.com/story/open-tail-1")
    engine = StoryEngine(
        StoryStateStore(tmp_path / "state"),
        StoryEpubSink(output, cover),
        adapter,
    )
    engine.initialize(story)

    # Trigger 1: chapter remains OPEN and stays the target.
    story = engine.trigger_next(story)
    assert story.chapters[0].status.value == "open"
    assert story.target_chapter_number == 1
    book = epub.read_epub(str(output))
    assert b"version 1" in book.get_item_with_id("chapter-1").content

    # Trigger 2: same OPEN chapter is refetched and replaced in-place.
    story = engine.trigger_next(story)
    assert story.chapters[0].status.value == "open"
    assert story.target_chapter_number == 1
    book = epub.read_epub(str(output))
    chapter = book.get_item_with_id("chapter-1")
    assert b"version 2" in chapter.content
    assert b"version 1" not in chapter.content

    # Trigger 3: chapter becomes COMPLETE; tail re-index discovers chapter 2.
    story = engine.trigger_next(story)
    assert story.chapters[0].status.value == "complete"
    assert story.target_chapter_number == 2
    assert [chapter.number for chapter in story.chapters] == [1, 2]
    assert adapter.refresh_calls == 3
