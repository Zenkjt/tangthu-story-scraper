from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from .bookshelf import BookshelfBackend, BookshelfRegistration
from ..application import StoryApplication
from ..story_catalog import StoryCatalogEpubSink
from ..story_epub import StoryEpubSink


class BookshelfWriteError(RuntimeError):
    """The Drive/shelf backend rejected an artifact write."""


class StoryRegistrationFlow:
    """GUI orchestration.

    User Drive contains only the two EPUB artifacts. Backend state/manifest/
    resolution stay outside the receiving folder.
    """

    USER_ID = "local-user"

    def __init__(
        self,
        application: StoryApplication,
        bookshelf_backend: BookshelfBackend,
        artifact_root: str | Path,
        cover_path: str | Path,
        notify: Callable[[str], None] | None = None,
    ):
        self.application = application
        self.bookshelf = bookshelf_backend
        self.artifact_root = Path(artifact_root)
        self.cover_path = Path(cover_path)
        self.notify = notify or (lambda _message: None)

    def inspect_bookshelf(self, folder_url: str) -> BookshelfRegistration | None:
        return self.bookshelf.inspect(folder_url)

    def register_story(
        self,
        registration: BookshelfRegistration,
        url: str,
        *,
        start_chapter_number: int | None = None,
    ):
        story_sink = self._story_sink(registration)
        catalog_sink = self._catalog_sink(registration)

        story = self.application.initialize(
            self.USER_ID,
            url.strip(),
            story_sink,
            start_chapter_number=start_chapter_number,
            catalog=catalog_sink,
        )

        # First trigger: exactly one chapter.
        story = self.application.trigger_next(
            self.USER_ID,
            story.story_id,
            story_sink,
            catalog=catalog_sink,
        )

        try:
            self._publish(registration, publish_catalog=True)
        except Exception as exc:
            raise BookshelfWriteError(
                "Không thể ghi sách vào tủ nhận sách. "
                "Hãy kiểm tra quyền chia sẻ Google Drive và bảo đảm "
                "Tàng Thư có quyền Editor / Có thể chỉnh sửa."
            ) from exc

        self.notify(f"Đăng ký truyện thành công: {story.title or story.story_id}")
        self.notify("Đã tải thành công chapter đầu tiên.")
        return story

    def load_current(self, story_id: str):
        return self.application.load_current(self.USER_ID, story_id)

    def set_target(self, story_id: str, number: int):
        return self.application.set_target(self.USER_ID, story_id, number)

    def trigger_current(self, registration: BookshelfRegistration, story_id: str):
        story_sink = self._story_sink(registration)
        catalog_sink = self._catalog_sink(registration)
        target_before = self.application.load_current(
            self.USER_ID, story_id
        ).target_chapter_number
        catalog_before = self._artifact_hash(
            registration, "0neStoryTOC.epub"
        )

        story = self.application.trigger_next(
            self.USER_ID,
            story_id,
            story_sink,
            catalog=catalog_sink,
        )

        catalog_after = self._artifact_hash(
            registration, "0neStoryTOC.epub"
        )
        try:
            self._publish(
                registration,
                publish_catalog=(catalog_before != catalog_after),
            )
        except Exception as exc:
            raise BookshelfWriteError(
                "Không thể ghi sách vào tủ nhận sách. "
                "Hãy kiểm tra quyền chia sẻ Google Drive và bảo đảm "
                "Tàng Thư có quyền Editor / Có thể chỉnh sửa."
            ) from exc

        self.notify(
            f"Đã chuyển/tải thành công chương {target_before or '—'}."
        )
        return story

    def _story_sink(self, registration: BookshelfRegistration):
        root = self.artifact_root / registration.folder_id
        root.mkdir(parents=True, exist_ok=True)
        return StoryEpubSink(root / "0neStory.epub", self.cover_path)

    def _catalog_sink(self, registration: BookshelfRegistration):
        root = self.artifact_root / registration.folder_id
        root.mkdir(parents=True, exist_ok=True)
        return StoryCatalogEpubSink(
            root / "0neStoryTOC.epub",
            self.cover_path,
        )

    def _artifact_hash(self, registration, filename: str) -> str | None:
        path = self.artifact_root / registration.folder_id / filename
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _publish(self, registration, *, publish_catalog: bool):
        root = self.artifact_root / registration.folder_id
        names = ["0neStory.epub"]
        if publish_catalog:
            names.append("0neStoryTOC.epub")

        for filename in names:
            path = root / filename
            if not path.exists():
                continue
            self.bookshelf.write(
                registration,
                filename,
                path.read_bytes(),
            )
