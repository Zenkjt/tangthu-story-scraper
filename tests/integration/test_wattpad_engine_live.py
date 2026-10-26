from pathlib import Path

from ebooklib import epub

from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore
from story_scraper.story_epub import StoryEpubSink
from story_scraper.adapters.platforms.wattpad import WattpadAdapter


STORY_URL = (
    "https://www.wattpad.com/story/"
    "107024873-chuy%E1%BB%87n-ng%C6%B0%E1%BB%9Di-kh%C3%B4ng-bi%E1%BA%BFt-d%E1%BA%A1-m%E1%BA%A1n"
)
ARTIFACT_DIR = Path("test-artifacts")


def test_wattpad_engine_builds_one_chapter_epub(tmp_path):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    output = ARTIFACT_DIR / "0neStory.epub"
    if output.exists():
        output.unlink()

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
    chapter = book.get_item_with_id("toc-1")

    assert chapter is not None
    assert len(chapter.content) > 1000

    # The live sample is Vietnamese. Fail the test if the chapter has
    # become mojibake/replacement characters before entering the EPUB.
    chapter_text = chapter.content.decode("utf-8", errors="replace")
    assert "Chương" in chapter_text or "chương" in chapter_text
    assert "người" in chapter_text or "Người" in chapter_text
    assert "\ufffd" not in chapter_text

    assert book.get_item_with_id("toc-2") is None
    assert output.exists()
    assert output.stat().st_size > 0
