from __future__ import annotations

import os

import pytest

from story_scraper.adapters.platforms.vnthuquan import VnThuQuanAdapter
from story_scraper.core.engine import StoryEngine
from story_scraper.core.state import StoryStateStore


LIVE_URL = os.getenv("VNTHUQUAN_TEST_URL")


class MemoryEpubSink:
    def __init__(self):
        self.created = False
        self.appended = []
        self.replaced = []

    def create(self, story):
        self.created = True

    def append(self, story, chapter, content):
        self.appended.append((chapter.number, content))

    def replace(self, story, chapter, content):
        self.replaced.append((chapter.number, content))


@pytest.mark.integration
def test_vnthuquan_engine_live(tmp_path):
    if not LIVE_URL:
        pytest.skip("VNTHUQUAN_TEST_URL is not set")

    adapter = VnThuQuanAdapter()
    story = adapter.build_index(LIVE_URL)

    assert story.chapters, "Live story page returned no chapters"

    sink = MemoryEpubSink()
    engine = StoryEngine(StoryStateStore(tmp_path), sink, adapter)

    engine.initialize(story)

    first_number = story.target_chapter_number
    assert first_number is not None
    assert sink.created is True

    engine.trigger_next(story)

    assert sink.appended
    assert sink.appended[0][0] == first_number
    assert story.chapters[0].content_hash
    assert story.chapters[0].status.value == "complete"

    next_number = story.target_chapter_number
    assert next_number is not None
    assert next_number != first_number

    engine.trigger_next(story)

    assert len(sink.appended) == 2
    assert sink.appended[1][0] == next_number
    assert story.target_chapter_number != next_number
