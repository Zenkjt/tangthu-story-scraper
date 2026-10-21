from story_scraper.core.base_adapter import BasePlatformAdapter
from story_scraper.core.models import Chapter, ChapterStatus


def test_normalize_and_dedupe():
    assert BasePlatformAdapter.normalize_url("HTTPS://WWW.Example.com/a//b/") == "https://www.example.com/a/b"
    urls = ["https://example.com/chapter/1/", "https://example.com/chapter/1", "https://example.com/chapter/2"]
    assert BasePlatformAdapter.dedupe_urls(urls) == ["https://example.com/chapter/1", "https://example.com/chapter/2"]


def test_chapter_number():
    assert BasePlatformAdapter.chapter_number("Chapter 12") == 12
    assert BasePlatformAdapter.chapter_number("Ep. 7 — Something") == 7
    assert BasePlatformAdapter.chapter_number("No number", fallback=3) == 3


def test_merge_preserves_download_state():
    existing = [Chapter(1, "Old", "https://x/1", ChapterStatus.COMPLETE, "hash")]
    incoming = [Chapter(1, "New", "https://x/1-new", ChapterStatus.PENDING)]
    merged = BasePlatformAdapter.merge_chapters(existing, incoming)
    assert merged[0].title == "New"
    assert merged[0].url == "https://x/1-new"
    assert merged[0].status == ChapterStatus.COMPLETE
    assert merged[0].content_hash == "hash"
