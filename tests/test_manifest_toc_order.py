from story_scraper.core.manifest import StoryManifestStore
from story_scraper.core.models import Chapter, ChapterStatus, Story


def test_manifest_roundtrip_preserves_toc_order_and_unnumbered_entries(tmp_path):
    store = StoryManifestStore(tmp_path / "manifest")
    story = Story(
        story_id="story-1",
        source_url="https://example.test/story/",
        site="static-html-family",
        title="Test Story",
        chapters=[
            Chapter(None, "Landing page", "https://example.test/story/", kind="page"),
            Chapter(1, "Chapter 1", "https://example.test/story/chapter-1", kind="chapter"),
            Chapter(None, "Foreword", "https://example.test/story/foreword", kind="section"),
        ],
        target_toc_index=3,
        registered_toc_index=1,
        index_url="https://example.test/story/",
    )
    story.normalize_toc()
    story.chapters[1].status = ChapterStatus.COMPLETE
    story.chapters[1].content_hash = "abc123"

    store.save("user-1", story)
    loaded = store.load("user-1", "story-1")

    assert loaded is not None
    assert [c.toc_index for c in loaded.chapters] == [1, 2, 3]
    assert [c.title for c in loaded.chapters] == ["Landing page", "Chapter 1", "Foreword"]
    assert [c.number for c in loaded.chapters] == [None, 1, None]
    assert loaded.target_toc_index == 3
    assert loaded.registered_toc_index == 1
    assert loaded.index_url == "https://example.test/story/"
    assert loaded.chapters[1].status is ChapterStatus.COMPLETE
    assert loaded.chapters[1].content_hash == "abc123"


def test_manifest_migrates_legacy_numbered_schema_v1(tmp_path):
    legacy = {
        "schema_version": 1,
        "story_id": "legacy-story",
        "source_url": "https://example.test/story",
        "site": "legacy",
        "chapters": [
            {"number": 2, "title": "Chapter 2", "url": "https://example.test/2"},
            {"number": 1, "title": "Chapter 1", "url": "https://example.test/1"},
        ],
        "target_chapter_number": 2,
    }

    story = StoryManifestStore._from_manifest(legacy)

    assert [c.number for c in story.chapters] == [2, 1]
    assert [c.toc_index for c in story.chapters] == [1, 2]
    assert story.target_toc_index == 1
