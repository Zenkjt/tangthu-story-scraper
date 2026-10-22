import os
from pathlib import Path

import pytest
from ebooklib import epub

from story_scraper.adapters.platforms.vnthuquan import VnThuQuanAdapter
from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore
from story_scraper.story_epub import StoryEpubSink

LIVE_URL = os.getenv("VNTHUQUAN_TEST_URL")

@pytest.mark.integration
def test_vnthuquan_story_epub_live(tmp_path):
    if not LIVE_URL:
        pytest.skip("VNTHUQUAN_TEST_URL is not set")
    adapter = VnThuQuanAdapter()
    story = adapter.build_index(LIVE_URL)
    assert story.chapters
    assert story.target_chapter_number is not None
    output = tmp_path / "0neStory.epub"
    cover = Path("assets/0neStory.bmp")
    assert cover.exists()
    sink = StoryEpubSink(output, cover)
    engine = StoryEngine(StoryStateStore(tmp_path / "state"), sink, adapter)
    engine.initialize(story)
    first_number = story.target_chapter_number
    engine.trigger_next(story)
    assert output.exists() and output.stat().st_size > 0
    book = epub.read_epub(str(output))
    chapter = book.get_item_with_id(f"chapter-{first_number}")
    assert chapter is not None and chapter.content
    assert story.chapters[0].content_hash
    assert story.chapters[0].status.value == "complete"
    next_number = story.target_chapter_number
    assert next_number is not None and next_number != first_number
    engine.trigger_next(story)
    book = epub.read_epub(str(output))
    next_chapter = book.get_item_with_id(f"chapter-{next_number}")
    assert next_chapter is not None and next_chapter.content
