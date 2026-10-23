from pathlib import Path

from story_scraper.core.registration import StoryRegistrationStore


def test_registration_is_per_user_and_source_url(tmp_path: Path):
    store = StoryRegistrationStore(tmp_path / "registration")

    assert store.get("user-a", "https://example.test/story") is None
    assert store.register("user-a", "https://example.test/story", "story-1") == "story-1"
    assert store.get("user-a", "https://example.test/story") == "story-1"
    assert store.get("user-b", "https://example.test/story") is None


def test_registration_does_not_replace_existing_story(tmp_path: Path):
    store = StoryRegistrationStore(tmp_path / "registration")

    assert store.register("user-a", "https://example.test/story", "story-1") == "story-1"
    assert store.register("user-a", "https://example.test/story", "story-2") == "story-1"
    assert store.get("user-a", "https://example.test/story") == "story-1"
