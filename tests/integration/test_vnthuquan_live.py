import os

import pytest

from story_scraper.adapters.platforms.vnthuquan import VnThuQuanAdapter


LIVE_URL = os.getenv("VNTHUQUAN_TEST_URL")


@pytest.mark.integration
def test_vnthuquan_live():
    if not LIVE_URL:
        pytest.skip("VNTHUQUAN_TEST_URL is not set")

    adapter = VnThuQuanAdapter()
    assert adapter.matches(LIVE_URL)

    story = adapter.build_index(LIVE_URL)

    assert story.story_id
    assert story.title
    assert story.source_url
    assert story.chapters, "Live story page returned no numeric chapters"

    first = story.chapters[0]
    assert first.number >= 1
    assert first.url

    content, complete = adapter.fetch_chapter(first)

    assert content.strip(), "First chapter returned empty content"
    assert complete is True
