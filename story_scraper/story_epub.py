from __future__ import annotations

import html
import io
import tempfile
from pathlib import Path

from ebooklib import epub
from PIL import Image

from .core.epub import EpubSink
from .core.models import Chapter, ChapterContent, Story


class StoryEpubSink(EpubSink):
    """Build 0neStory.epub from scratch for exactly one fetched entry."""

    COVER_PATH = Path(__file__).resolve().parents[1] / "assets" / "0neStory.bmp"

    def __init__(
        self,
        output_path: str | Path,
        *,
        language: str = "vi",
        publisher: str = "Tàng Thư",
    ):
        self.output_path = Path(output_path)
        self.language = language
        self.publisher = publisher

    def create(self, story: Story) -> None:
        # Registration creates a valid EPUB shell with the fixed default cover.
        self._write(self._new_book(story))

    def append(
        self,
        story: Story,
        chapter: Chapter,
        content: str | ChapterContent,
    ) -> None:
        self._write(self._single_entry_book(story, chapter, content))

    def replace(
        self,
        story: Story,
        chapter: Chapter,
        content: str | ChapterContent,
    ) -> None:
        self._write(self._single_entry_book(story, chapter, content))

    def _base_book(self, story: Story) -> epub.EpubBook:
        book = epub.EpubBook()
        book.set_identifier(f"tangthu-story-{story.story_id}")
        book.set_title(story.title or story.story_id)
        book.set_language(self.language)
        book.add_author(story.author or "Tàng Thư")
        book.add_metadata("DC", "publisher", self.publisher)
        book.add_metadata("DC", "source", story.source_url)
        return book

    def _new_book(self, story: Story) -> epub.EpubBook:
        book = self._base_book(story)
        self._add_cover(book)
        return book

    def _single_entry_book(
        self,
        story: Story,
        chapter: Chapter,
        content: str | ChapterContent,
    ) -> epub.EpubBook:
        story.normalize_toc()
        book = self._base_book(story)
        self._add_cover(book)

        item = self._chapter_item(book, chapter, content)
        book.add_item(item)
        self._add_assets(book, content)

        book.toc = (
            epub.Link(
                item.file_name,
                chapter.title or f"Vị trí {chapter.toc_index}",
                item.id,
            ),
        )

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["cover", item]
        return book

    def _add_cover(self, book: epub.EpubBook) -> None:
        if not self.COVER_PATH.exists():
            raise FileNotFoundError(
                f"Không tìm thấy bìa mặc định: {self.COVER_PATH}"
            )

        with Image.open(self.COVER_PATH) as image:
            gray = image.convert("L")
            buffer = io.BytesIO()
            gray.save(buffer, format="JPEG", quality=90, optimize=True)
            cover_bytes = buffer.getvalue()

        image_item = epub.EpubItem(
            uid="cover-image",
            file_name="images/cover.jpg",
            media_type="image/jpeg",
            content=cover_bytes,
        )
        book.add_item(image_item)

        cover = epub.EpubHtml(
            uid="cover",
            title="Bìa",
            file_name="cover.xhtml",
            lang=self.language,
        )
        cover.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            "<head><title>Bìa</title></head>"
            '<body style="margin:0;text-align:center;">'
            '<img src="images/cover.jpg" alt="Bìa 0neStory" '
            'style="max-width:100%;height:auto;" />'
            "</body></html>"
        )
        book.add_item(cover)
        book.add_metadata("OPF", "cover", "cover-image")

    @staticmethod
    def _chapter_id(chapter: Chapter) -> str:
        return f"toc-{chapter.toc_index}"

    def _chapter_item(
        self,
        book: epub.EpubBook,
        chapter: Chapter,
        content: str | ChapterContent,
    ) -> epub.EpubHtml:
        title = chapter.title or f"Vị trí {chapter.toc_index}"
        item = epub.EpubHtml(
            title=title,
            file_name=f"toc-{chapter.toc_index}.xhtml",
            lang=self.language,
            uid=self._chapter_id(chapter),
        )
        item.content = self._chapter_html(chapter, content)
        return item

    @staticmethod
    def _html_and_assets(content: str | ChapterContent) -> tuple[str, list]:
        if isinstance(content, ChapterContent):
            return content.html, content.assets
        return content, []

    def _add_assets(
        self,
        book: epub.EpubBook,
        content: str | ChapterContent,
    ) -> None:
        _, assets = self._html_and_assets(content)
        for asset in assets:
            uid = "asset-" + asset.path.replace("/", "-").replace(".", "-")
            if book.get_item_with_id(uid) is not None:
                continue
            book.add_item(
                epub.EpubItem(
                    uid=uid,
                    file_name=asset.path,
                    media_type=asset.media_type,
                    content=asset.content,
                )
            )

    def _chapter_html(
        self,
        chapter: Chapter,
        content: str | ChapterContent,
    ) -> str:
        body, _ = self._html_and_assets(content)
        safe_title = html.escape(
            chapter.title or f"Vị trí {chapter.toc_index}"
        )
        return (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            f"<head><title>{safe_title}</title></head>"
            f"<body><h1>{safe_title}</h1>{body}</body></html>"
        )

    def _write(self, book: epub.EpubBook) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f"{self.output_path.stem}-",
            suffix=".epub",
            dir=self.output_path.parent,
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)
        try:
            epub.write_epub(str(temp_path), book)
            temp_path.replace(self.output_path)
        finally:
            temp_path.unlink(missing_ok=True)
