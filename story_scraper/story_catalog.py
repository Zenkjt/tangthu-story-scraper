from __future__ import annotations

import html
import tempfile
from pathlib import Path

from ebooklib import epub

from .core.models import Story


class StoryCatalogEpubSink:
    """Navigation EPUB containing the ordered source TOC, not chapter-only data."""

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
        self._write(self._build(story))

    def update(self, story: Story) -> None:
        self.create(story)

    def _build(self, story: Story) -> epub.EpubBook:
        story.normalize_toc()

        book = epub.EpubBook()
        book.set_identifier(f"tangthu-story-catalog-{story.story_id}")
        book.set_title(story.title or story.story_id)
        book.set_language(self.language)
        book.add_author(story.author or "Tàng Thư")
        book.add_metadata("DC", "publisher", self.publisher)
        book.add_metadata("DC", "source", story.source_url)

        info = epub.EpubHtml(
            title="Thông tin",
            file_name="story.xhtml",
            lang=self.language,
        )
        info.content = self._info_html(story)
        book.add_item(info)

        toc = epub.EpubHtml(
            title="Mục lục",
            file_name="toc.xhtml",
            lang=self.language,
        )
        entries = []
        for entry in sorted(story.chapters, key=lambda item: item.toc_index):
            title = html.escape(entry.title or f"Vị trí {entry.toc_index}")
            url = html.escape(entry.url, quote=True)
            marker = (
                ' <strong>— Vị trí đăng ký</strong>'
                if entry.toc_index == story.registered_toc_index
                else ""
            )
            entries.append(
                f'<li value="{entry.toc_index}"><a href="{url}">'
                f'{title}</a>{marker}</li>'
            )

        toc.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            '<head><title>Mục lục</title></head><body>'
            f'<h1>{html.escape(story.title or story.story_id)}</h1>'
            '<ol>' + "".join(entries) + "</ol></body></html>"
        )
        book.add_item(toc)

        book.toc = tuple(
            epub.Link(
                entry.url,
                entry.title or f"Vị trí {entry.toc_index}",
                f"toc-{entry.toc_index}",
            )
            for entry in sorted(story.chapters, key=lambda item: item.toc_index)
        )
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", info, toc]
        return book

    @staticmethod
    def _info_html(story: Story) -> str:
        title = html.escape(story.title or story.story_id)
        author = html.escape(story.author or "Không rõ")
        registered = (
            str(story.registered_toc_index)
            if story.registered_toc_index is not None
            else "Không xác định"
        )
        return (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            f"<head><title>{title}</title></head><body>"
            f"<h1>{title}</h1><p>Tác giả: {author}</p>"
            f"<p>Số mục lục đã biết: {len(story.chapters)}</p>"
            f"<p>Vị trí đăng ký: {registered}</p></body></html>"
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
