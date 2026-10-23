from __future__ import annotations

import html
import io
import tempfile
from pathlib import Path

from ebooklib import epub
from PIL import Image

from .core.models import Story


class StoryCatalogEpubSink:
    """Navigation EPUB: metadata, cover, and the complete discovered chapter TOC only."""

    def __init__(self, output_path: str | Path, cover_path: str | Path,
                 *, language: str = "vi", publisher: str = "Tàng Thư"):
        self.output_path = Path(output_path)
        self.cover_path = Path(cover_path)
        self.language = language
        self.publisher = publisher

    def create(self, story: Story) -> None:
        self._write(self._build(story))

    def update(self, story: Story) -> None:
        self.create(story)

    def _build(self, story: Story) -> epub.EpubBook:
        book = epub.EpubBook()
        book.set_identifier(f"tangthu-story-catalog-{story.story_id}")
        book.set_title(story.title or story.story_id)
        book.set_language(self.language)
        book.add_author(story.author or "Tàng Thư")
        book.add_metadata("DC", "publisher", self.publisher)
        book.add_metadata("DC", "source", story.source_url)
        self._add_cover(book, story)

        info = epub.EpubHtml(title="Thông tin", file_name="story.xhtml", lang=self.language)
        info.content = self._info_html(story)
        book.add_item(info)

        toc = epub.EpubHtml(title="Danh sách chương", file_name="toc.xhtml", lang=self.language)
        entries = []
        for chapter in sorted(story.chapters, key=lambda item: item.number):
            title = html.escape(chapter.title or f"Chương {chapter.number}")
            url = html.escape(chapter.url, quote=True)
            entries.append(f'<li><a href="{url}">{title}</a></li>')
        toc.content = ('<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
                       '<head><title>Danh sách chương</title></head><body>'
                       f'<h1>{html.escape(story.title or story.story_id)}</h1>'
                       '<ol>' + ''.join(entries) + '</ol></body></html>')
        book.add_item(toc)

        book.toc = tuple(epub.Link(chapter.url,
                                   chapter.title or f"Chương {chapter.number}",
                                   f"chapter-{chapter.number}")
                         for chapter in sorted(story.chapters, key=lambda item: item.number))
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", info, toc]
        return book

    def _add_cover(self, book: epub.EpubBook, story: Story) -> None:
        with Image.open(io.BytesIO(self.cover_path.read_bytes())) as source:
            image = source.convert("L")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, progressive=False, optimize=True, subsampling=2)
        cover_item = epub.EpubItem(uid="cover-image", file_name="images/cover.jpg",
                                   media_type="image/jpeg", content=buffer.getvalue())
        cover_item.properties = ["cover-image"]
        book.add_item(cover_item)
        book.add_metadata("OPF", "meta", "", {"name": "cover", "content": "cover-image"})
        cover = epub.EpubHtml(title=story.title or "0neStory", file_name="cover.xhtml", lang=self.language)
        cover.content = ('<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
                         '<head><title>0neStory</title></head><body style="margin:0;padding:0">'
                         '<img src="images/cover.jpg" alt="Tàng Thư — 0neStory" '
                         'style="display:block;width:100%;height:auto" /></body></html>')
        cover.add_item(cover_item)
        book.add_item(cover)

    @staticmethod
    def _info_html(story: Story) -> str:
        title = html.escape(story.title or story.story_id)
        author = html.escape(story.author or "Không rõ")
        return ('<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
                f'<head><title>{title}</title></head><body>'
                f'<h1>{title}</h1><p>Tác giả: {author}</p>'
                f'<p>Số chương đã biết: {len(story.chapters)}</p></body></html>')

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
