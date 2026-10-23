from pathlib import Path

from story_scraper.core.bookshelf import BookshelfRegistrationStore


def test_register_bookshelf_uses_folder_name(tmp_path: Path):
    folder = tmp_path / "My Bookshelf"
    store = BookshelfRegistrationStore()

    registration = store.register(folder)

    assert registration.name == "My Bookshelf"
    assert registration.path == str(folder.resolve())
    assert registration.story_id is None
    assert (folder / ".tangthu-bookshelf.json").exists()


def test_bookshelf_registration_remembers_story(tmp_path: Path):
    store = BookshelfRegistrationStore()
    store.register(tmp_path)

    updated = store.set_story(tmp_path, "story-123")
    loaded = store.load(tmp_path)

    assert updated.story_id == "story-123"
    assert loaded is not None
    assert loaded.story_id == "story-123"
