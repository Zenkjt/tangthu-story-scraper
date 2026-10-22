from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.adapters.platforms.static_html import StaticHTMLFamilyAdapter
from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore
from story_scraper.story_epub import StoryEpubSink


STORY_URL = "https://truyenfull.live/than-dao-dan-ton-6060282/"


def test_truyenfull_engine_fetches_exactly_one_chapter(tmp_path):
    cover = tmp_path / "0neStory.bmp"
    output = tmp_path / "0neStory.epub"
    Image.new("L", (480, 800), 255).save(cover, format="BMP")

    adapter = StaticHTMLFamilyAdapter()
    story = adapter.build_index(STORY_URL)

    assert story.title == "Thần Đạo Đan Tôn"
    assert len(story.chapters) >= 2
    assert story.target_chapter_number == 1
    assert story.chapters[0].number == 1
    assert story.chapters[0].url.endswith("/chuong-1/")

    engine = StoryEngine(
        StoryStateStore(tmp_path / "state"),
        StoryEpubSink(output, cover),
        adapter,
    )
    engine.initialize(story)

    # One trigger must fetch exactly one chapter.
    story = engine.trigger_next(story)

    assert story.chapters[0].status.value == "complete"
    assert story.target_chapter_number == 2
    assert story.chapters[0].content_hash

    book = epub.read_epub(str(output))
    chapter_1 = book.get_item_with_id("chapter-1")
    chapter_2 = book.get_item_with_id("chapter-2")

    assert chapter_1 is not None
    assert len(chapter_1.content) > 1000
    assert chapter_2 is None

    chapter_items = [
        item for item in book.get_items()
        if item.get_type() == 9 and item.get_id().startswith("chapter-")
    ]
    assert len(chapter_items) == 1
