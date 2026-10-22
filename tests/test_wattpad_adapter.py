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


def test_story_url_extracts_story_id():
    assert WattpadAdapter.matches(STORY_URL)
    assert WattpadAdapter.extract_ids(STORY_URL) == (107024873, None)


def test_part_url_extracts_part_id():
    assert WattpadAdapter.matches(PART_URL)
    assert WattpadAdapter.extract_ids(PART_URL) == (None, "402782528")


def test_manifest_maps_part_id_to_sequential_chapter_number():
    adapter = WattpadAdapter()
    story = adapter.build_story_from_manifest(
        story_id=107024873,
        source_url=STORY_URL,
        title="Chuyện người không biết dạ mạn",
        author="Tác giả",
        parts=[
            {"id": 402782528, "title": "Chương 1", "url": PART_URL},
            {"id": 402782529, "title": "Chương 2"},
        ],
        target_external_id="402782528",
    )

    assert story.story_id == "107024873"
    assert [c.number for c in story.chapters] == [1, 2]
    assert [c.external_id for c in story.chapters] == ["402782528", "402782529"]
    assert story.target_chapter_number == 1
