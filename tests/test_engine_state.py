from story_scraper.core.models import Chapter, ChapterStatus, Story


def test_explicit_target_round_trip():
    story = Story("s1", "https://example.com/story", "example",
                  chapters=[Chapter(10, "Ten", "https://example.com/10"),
                            Chapter(20, "Twenty", "https://example.com/20")],
                  target_chapter_number=20)
    assert Story.from_dict(story.as_dict()).target_chapter_number == 20


def test_legacy_current_index_migrates():
    data = {"story_id": "s1", "source_url": "https://example.com/story",
            "site": "example",
            "chapters": [{"number": 10, "title": "Ten", "url": "https://example.com/10"},
                         {"number": 20, "title": "Twenty", "url": "https://example.com/20"}],
            "current_index": 1}
    assert Story.from_dict(data).target_chapter_number == 20


def test_legacy_exhausted_index_requests_tail_refresh():
    data = {"story_id": "s1", "source_url": "https://example.com/story",
            "site": "example",
            "chapters": [{"number": 10, "title": "Ten", "url": "https://example.com/10"},
                         {"number": 20, "title": "Twenty", "url": "https://example.com/20"}],
            "current_index": 2}
    assert Story.from_dict(data).target_chapter_number is None


def test_open_chapter_stays_target():
    story = Story("s1", "https://example.com/story", "example",
                  chapters=[Chapter(10, "Ten", "https://example.com/10", ChapterStatus.OPEN)],
                  target_chapter_number=10)
    assert story.target_chapter_number == 10
