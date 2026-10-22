from story_scraper.adapters.platforms.wattpad import WattpadAdapter


STORY_URL = (
    "https://www.wattpad.com/story/107024873-"
    "chuy%E1%BB%87n-ng%C6%B0%E1%BB%9Di-kh%C3%B4ng-bi%E1%BA%BFt-"
    "d%E1%BA%A1-m%E1%BA%A1n"
)

PART_URL = (
    "https://www.wattpad.com/402782528-"
    "chuy%E1%BB%87n-ng%C6%B0%E1%BB%9Di-kh%C3%B4ng-bi%E1%BA%BFt-"
    "d%E1%BA%A1-m%E1%BA%A1n-ch%C6%B0%C6%A1ng-1"
)


def test_wattpad_url_ids():
    assert WattpadAdapter.matches(STORY_URL)
    assert WattpadAdapter.extract_ids(STORY_URL) == (107024873, None)

    assert WattpadAdapter.matches(PART_URL)
    assert WattpadAdapter.extract_ids(PART_URL) == (None, "402782528")


def test_wattpad_manifest_target():
    adapter = WattpadAdapter()
    story = adapter.fetch_story(STORY_URL)

    assert story.story_id == "107024873"
    assert story.title == "Chuyện người không biết - Dạ Mạn"
    assert story.author == "hi"
    assert len(story.chapters) == 45
    assert story.chapters[0].number == 1
    assert story.chapters[0].external_id == "402782528"


def test_wattpad_part_url_resolves_target():
    adapter = WattpadAdapter()
    story = adapter.fetch_story(PART_URL)

    assert story.story_id == "107024873"
    assert story.target_chapter_number == 1
    assert story.chapters[0].external_id == "402782528"


def test_wattpad_fetch_one_chapter():
    adapter = WattpadAdapter()
    story = adapter.fetch_story(PART_URL)

    chapter = story.chapters[story.target_chapter_number - 1]
    content, complete = adapter.fetch_chapter(chapter)

    assert complete is True
    assert len(content.html) > 1000
    assert "Chương" in content.html or "chương" in content.html
