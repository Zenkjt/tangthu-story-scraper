from __future__ import annotations

from pathlib import Path

from .bookshelf import BookshelfRegistration, BookshelfRegistrationStore


class BookshelfStoryFlow:
    """GUI-facing orchestration for one registered bookshelf."""

    USER_ID = "local-user"

    def __init__(self, application, registration_store: BookshelfRegistrationStore | None = None):
        self.application = application
        self.registrations = registration_store or BookshelfRegistrationStore()

    def register_bookshelf(self, folder: str | Path) -> BookshelfRegistration:
        return self.registrations.register(folder)

    def load_registration(self, folder: str | Path) -> BookshelfRegistration | None:
        return self.registrations.load(folder)

    def browse(self, folder: str | Path, url: str = "", start_chapter_number: int | None = None):
        registration = self.registrations.load(folder)
        if registration is None:
            raise ValueError("Bookshelf is not registered")

        epub, catalog = self._sinks(registration.path)
        if registration.story_id is None:
            if not url.strip():
                raise ValueError("Story URL is required for first registration")
            story = self.application.initialize(
                self.USER_ID,
                url.strip(),
                epub,
                start_chapter_number=start_chapter_number,
            )
            story = self.application.trigger_next(self.USER_ID, story.story_id, epub)
            self.registrations.set_story(registration.path, story.story_id)
            return story

        if not url.strip():
            story = self.application.load_current(self.USER_ID, registration.story_id)
            return story

        raise StoryReplacementRequired(registration.story_id, url.strip())

    def confirm_replace(self, folder: str | Path, url: str, start_chapter_number: int | None = None):
        registration = self.registrations.load(folder)
        if registration is None or registration.story_id is None:
            return self.browse(folder, url, start_chapter_number)

        self._remove_story_files(registration.path)
        self._remove_story_state(registration.path, registration.story_id)
        self.registrations.clear_story(registration.path)
        return self.browse(folder, url, start_chapter_number)

    def load_current(self, user_id: str, story_id: str):
        return self.application.load_current(user_id, story_id)

    def set_target(self, folder: str | Path, number: int):
        registration = self._require_registration(folder)
        return self.application.set_target(self.USER_ID, registration.story_id, number)

    def trigger_current(self, folder: str | Path):
        registration = self._require_registration(folder)
        epub, _ = self._sinks(registration.path)
        return self.application.trigger_next(self.USER_ID, registration.story_id, epub)

    def _require_registration(self, folder):
        registration = self.registrations.load(folder)
        if registration is None or registration.story_id is None:
            raise ValueError("No story is registered in this bookshelf")
        return registration

    def _sinks(self, folder: str):
        from ..story_catalog import StoryCatalogEpubSink
        from ..story_epub import StoryEpubSink

        root = Path(folder)
        meta = root / ".tangthu"
        meta.mkdir(exist_ok=True)
        cover = meta / "cover.jpg"
        if not cover.exists():
            self._make_cover(cover)
        return (
            StoryEpubSink(root / "0neStory.epub", cover),
            StoryCatalogEpubSink(root / "0neStoryTOC.epub", cover),
        )

    @staticmethod
    def _make_cover(path: Path):
        from PIL import Image, ImageDraw

        image = Image.new("L", (600, 900), 255)
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 580, 880), outline=0, width=4)
        draw.text((70, 410), "TÀNG THƯ\n0neStory", fill=0, spacing=18)
        image.save(path, format="JPEG", quality=90)

    @staticmethod
    def _remove_story_files(folder: str):
        root = Path(folder)
        for name in ("0neStory.epub", "0neStoryTOC.epub"):
            (root / name).unlink(missing_ok=True)

    @staticmethod
    def _remove_story_state(folder: str, story_id: str):
        meta = Path(folder) / ".tangthu"
        # The application's state/manifest roots are bookshelf-local in this GUI flow.
        for root_name in ("state", "manifest"):
            path = meta / root_name
            if not path.exists():
                continue
            import hashlib
            digest = hashlib.sha256(story_id.encode("utf-8")).hexdigest()
            if root_name == "state":
                (path / f"{story_id}.json").unlink(missing_ok=True)
            else:
                user_hash = hashlib.sha256(BookshelfStoryFlow.USER_ID.encode("utf-8")).hexdigest()
                (path / user_hash / f"{digest}.json").unlink(missing_ok=True)


class StoryReplacementRequired(Exception):
    def __init__(self, current_story_id: str, new_url: str):
        super().__init__("A story is already registered in this bookshelf")
        self.current_story_id = current_story_id
        self.new_url = new_url
