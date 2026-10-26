from pathlib import Path

from ebooklib import epub
from PIL import Image

from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore
from story_scraper.story_epub import StoryEpubSink
from story_scraper.adapters.platforms.wattpad import WattpadAdapter


STORY_URL = "https://www.wattpad.com/story/107024873-chuy%E1%BB%87n-ng%C6%B0%E1%BB%9Di-kh%C3%B4ng-bi%E1%BA%BFt-d%E1%BA%A1-m%E1%BA%A1n"
ARTIFACT_DIR = Path("test-artifacts")


def test_wattpad_engine_builds_story_epub(tmp_path):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    output = ARTIFACT_DIR / "0neStory.epub"
    if output.exists():
        output.unlink()

    cover = tmp_path / "0neStory.bmp"
    Image.new("L", (480, 800), 255).save(cover, format="BMP")

    adapter = WattpadAdapter()
    story = adapter.build_index(STORY_URL)

    assert story.story_id == "107024873"
    assert len(story.chapters) == 45
    assert story.target_chapter_number == 1
    assert story.chapters[0].external_id == "402782528"

    engine = StoryEngine(
        StoryStateStore(tmp_path / "state"),
        StoryEpubSink(output),
        adapter,
    )
    engine.initialize(story)

    story = engine.trigger_next(story)
    assert story.chapters[0].status.value == "complete"
    assert story.target_chapter_number == 2

    book = epub.read_epub(str(output))
    assert book.get_item_with_id("toc-1") is not None
    assert len(book.get_item_with_id("toc-1").content) > 1000
    assert book.get_item_with_id("toc-2") is None

    story = engine.trigger_next(story)
    assert story.chapters[1].status.value == "complete"
    assert story.target_chapter_number == 3

    book = epub.read_epub(str(output))
    assert book.get_item_with_id("toc-2") is not None
    assert book.get_item_with_id("toc-3") is None

    assert output.exists()
    assert output.stat().st_size > 0
