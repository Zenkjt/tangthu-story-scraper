from story_scraper.core.models import Chapter, ChapterStatus, Story
from story_scraper.core.manifest import StoryManifestStore


def make_story():
    return Story(
        story_id="truyenfull.live/than-dao-dan-ton-6060282",
        source_url="https://truyenfull.live/than-dao-dan-ton-6060282/",
        site="truyenfull.live",
        title="Thần Đạo Đan Tôn",
        author="Cô Đơn Địa Phi",
        chapters=[
            Chapter(2, "Chương 2", "https://example.test/chuong-2/"),
            Chapter(1, "Chương 1", "https://example.test/chuong-1/"),
        ],
        target_chapter_number=2,
    )


def test_manifest_round_trip_is_per_user_and_story(tmp_path):
    store = StoryManifestStore(tmp_path)
    story = make_story()

    store.save("user-a", story)

    loaded = store.load("user-a", story.story_id)
    assert loaded is not None
    assert loaded.title == story.title
    assert [c.number for c in loaded.chapters] == [1, 2]
    assert loaded.target_chapter_number == 1
    assert store.load("user-b", story.story_id) is None


def test_manifest_does_not_store_runtime_state_or_content(tmp_path):
    store = StoryManifestStore(tmp_path)
    story = make_story()
    story.chapters[0].content_hash = "secret-content-hash"
    story.chapters[0].status = ChapterStatus.COMPLETE

    store.save("user-a", story)
    raw = store.path_for("user-a", story.story_id).read_text(encoding="utf-8")

    assert "secret-content-hash" not in raw
    assert '"status"' not in raw
    assert '"target_chapter_number"' not in raw
    assert '"content"' not in raw
