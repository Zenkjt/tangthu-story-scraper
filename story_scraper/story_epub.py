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
    """Persistent EPUB artifact for one continuously updated story."""

    def __init__(self, output_path: str | Path, cover_path: str | Path,
                 *, language: str = "vi", publisher: str = "Tàng Thư"):
        self.output_path = Path(output_path)
        self.cover_path = Path(cover_path)
        self.language = language
        self.publisher = publisher

    def create(self, story: Story) -> None:
        self._write(self._new_book(story))

    def append(self, story: Story, chapter: Chapter, content: str | ChapterContent) -> None:
        if not self.output_path.exists():
            self.create(story)
        book = epub.read_epub(str(self.output_path))
        self._sync_metadata(book, story)
        item = self._chapter_item(book, chapter, content)
        if book.get_item_with_id(item.id) is None:
            book.add_item(item)
            self._add_assets(book, content)
        self._sync_navigation(book, story)
        self._write(book)

    def replace(self, story: Story, chapter: Chapter, content: str | ChapterContent) -> None:
        if not self.output_path.exists():
            self.create(story)
        book = epub.read_epub(str(self.output_path))
        self._sync_metadata(book, story)
        item_id = self._chapter_id(chapter)
        existing = book.get_item_with_id(item_id)
        if existing is None:
            book.add_item(self._chapter_item(book, chapter, content))
        else:
            existing.title = chapter.title or existing.title
            existing.content = self._chapter_html(chapter, content)
        self._add_assets(book, content)
        self._sync_navigation(book, story)
        self._write(book)

    def _new_book(self, story: Story) -> epub.EpubBook:
        book = epub.EpubBook()
        book.set_identifier(f"tangthu-story-{story.story_id}")
        book.set_title(story.title or story.story_id)
        book.set_language(self.language)
        book.add_author(story.author or "Tàng Thư")
        book.add_metadata("DC", "publisher", self.publisher)
        book.add_metadata("DC", "source", story.source_url)
        self._add_cover(book, story)
        info = epub.EpubHtml(title="Thông tin", file_name="story.xhtml", lang=self.language)
        info.content = self._story_html(story)
        book.add_item(info)
        self._sync_navigation(book, story)
        return book

    def _add_cover(self, book: epub.EpubBook, story: Story) -> None:
        with Image.open(io.BytesIO(self.cover_path.read_bytes())) as source:
            image = source.convert("L")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, progressive=False,
                       optimize=True, subsampling=2)
        cover_item = epub.EpubItem(uid="cover-image", file_name="images/cover.jpg",
                                   media_type="image/jpeg", content=buffer.getvalue())
        cover_item.properties = ["cover-image"]
        book.add_item(cover_item)
        book.add_metadata("OPF", "meta", "", {"name": "cover", "content": "cover-image"})
        cover = epub.EpubHtml(title=story.title or "0neStory", file_name="cover.xhtml", lang=self.language)
        cover.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            "<head><title>0neStory</title></head>"
            '<body style="margin:0;padding:0">'
            '<img src="images/cover.jpg" alt="Tàng Thư — 0neStory" '
            'style="display:block;width:100%;height:auto" />'
            "</body></html>"
        )
        cover.add_item(cover_item)
        book.add_item(cover)

    @staticmethod
    def _chapter_id(chapter: Chapter) -> str:
        return f"chapter-{chapter.number}"

    def _chapter_item(self, book: epub.EpubBook, chapter: Chapter,
                      content: str | ChapterContent) -> epub.EpubHtml:
        item = epub.EpubHtml(title=chapter.title or f"Chương {chapter.number}",
                             file_name=f"chapter-{chapter.number}.xhtml",
                             lang=self.language, uid=self._chapter_id(chapter))
        item.content = self._chapter_html(chapter, content)
        return item

    @staticmethod
    def _html_and_assets(content: str | ChapterContent) -> tuple[str, list]:
        if isinstance(content, ChapterContent):
            return content.html, content.assets
        return content, []

    def _add_assets(self, book: epub.EpubBook, content: str | ChapterContent) -> None:
        _, assets = self._html_and_assets(content)
        for asset in assets:
            uid = "asset-" + asset.path.replace("/", "-").replace(".", "-")
            if book.get_item_with_id(uid) is not None:
                continue
            book.add_item(epub.EpubItem(uid=uid, file_name=asset.path,
                                       media_type=asset.media_type, content=asset.content))

    def _chapter_html(self, chapter: Chapter, content: str | ChapterContent) -> str:
        body, _ = self._html_and_assets(content)
        safe_title = html.escape(chapter.title or f"Chương {chapter.number}")
        return ('<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
                f"<head><title>{safe_title}</title></head>"
                f"<body><h1>{safe_title}</h1>{body}</body></html>")

    def _story_html(self, story: Story) -> str:
        title = html.escape(story.title or story.story_id)
        author = html.escape(story.author or "Không rõ")
        source = html.escape(story.source_url)
        return ('<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
                f"<head><title>{title}</title></head>"
                f"<body><h1>{title}</h1><p>Tác giả: {author}</p>"
                f'<p><a href="{source}">Nguồn truyện</a></p></body></html>')

    def _sync_metadata(self, book: epub.EpubBook, story: Story) -> None:
        book.set_title(story.title or story.story_id)
        book.set_language(self.language)

    def _sync_navigation(self, book: epub.EpubBook, story: Story) -> None:
        entries = []
        for chapter in sorted(story.chapters, key=lambda item: item.number):
            item = book.get_item_with_id(self._chapter_id(chapter))
            if item is not None:
                entries.append((chapter, item))
        book.toc = tuple(epub.Link(item.file_name,
                                   chapter.title or f"Chương {chapter.number}",
                                   item.id) for chapter, item in entries)
        if book.get_item_with_id("nav") is None:
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
        fixed = {item.file_name: item for item in book.get_items()
                 if item.file_name in {"cover.xhtml", "story.xhtml"}}
        spine = [fixed[name] for name in ("cover.xhtml", "story.xhtml") if name in fixed]
        spine.extend(item for _, item in entries)
        book.spine = spine

    def _write(self, book: epub.EpubBook) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=f"{self.output_path.stem}-", suffix=".epub",
                                          dir=self.output_path.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            epub.write_epub(str(temp_path), book)
            temp_path.replace(self.output_path)
        finally:
            temp_path.unlink(missing_ok=True)
