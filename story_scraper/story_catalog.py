from __future__ import annotations

import html
import io
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from ebooklib import epub
from PIL import Image

from .core.models import Story


class StoryCatalogEpubSink:
    """Valid navigation EPUB containing the complete ordered source TOC."""

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

        has_cover = self._add_cover(book, story)

        info = epub.EpubHtml(
            uid="info",
            title="Thông tin",
            file_name="info.xhtml",
            lang=self.language,
        )
        info.content = self._info_html(story)
        book.add_item(info)

        toc_page = epub.EpubHtml(
            uid="toc",
            title="Mục lục",
            file_name="toc.xhtml",
            lang=self.language,
        )
        book.add_item(toc_page)

        entry_pages = []
        links = []
        list_items = []

        for entry in sorted(story.chapters, key=lambda item: item.toc_index):
            uid = f"entry-{entry.toc_index}"
            file_name = f"entries/{entry.toc_index:04d}.xhtml"
            title = entry.title or f"Vị trí {entry.toc_index}"
            page = epub.EpubHtml(
                uid=uid,
                title=title,
                file_name=file_name,
                lang=self.language,
            )
            page.content = self._entry_html(story, entry)
            book.add_item(page)
            entry_pages.append(page)

            marker = (
                " — Vị trí đăng ký"
                if entry.toc_index == story.registered_toc_index
                else ""
            )
            list_items.append(
                f'<li><a href="{html.escape(file_name, quote=True)}">'
                f'<strong>{entry.toc_index}.</strong> '
                f'{html.escape(title)}{html.escape(marker)}</a></li>'
            )
            links.append(
                epub.Link(
                    file_name,
                    f"{entry.toc_index}. {title}",
                    uid,
                )
            )

        toc_page.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            "<head><title>Mục lục</title></head><body>"
            f"<h1>{html.escape(story.title or story.story_id)}</h1>"
            f"<p>Tổng mục lục: {len(story.chapters)}</p>"
            "<ol>"
            + "".join(list_items)
            + "</ol></body></html>"
        )

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.toc = tuple(links)

        spine = ["nav", info, toc_page, *entry_pages]
        if has_cover:
            spine.insert(0, "cover")
        book.spine = spine
        return book

    def _add_cover(self, book: epub.EpubBook, story: Story) -> bool:
        cover_url = self._cover_url(story)
        if not cover_url:
            return False

        try:
            content, media_type = self._download_cover(cover_url)
        except Exception:
            return False

        image_item = epub.EpubItem(
            uid="cover-image",
            file_name="images/cover.jpg",
            media_type=media_type,
            content=content,
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
            '<img src="images/cover.jpg" alt="Bìa" '
            'style="max-width:100%;height:auto;" />'
            "</body></html>"
        )
        book.add_item(cover)
        book.add_metadata(
            "OPF",
            "meta",
            "",
            {"name": "cover", "content": "cover-image"},
        )
        return True

    @classmethod
    def _cover_url(cls, story: Story) -> str | None:
        if story.cover_url:
            return story.cover_url

        request = Request(
            story.source_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TangThuStoryScraper/1.0)"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                page = response.read().decode("utf-8", errors="ignore")
                final_url = response.geturl()
        except Exception:
            return None

        for name in ("og:image", "twitter:image", "twitter:image:src"):
            pattern = re.compile(
                rf'<meta[^>]+(?:property|name)\s*=\s*["\']'
                rf'{re.escape(name)}["\'][^>]+content\s*=\s*["\']'
                rf'([^"\']+)',
                re.I,
            )
            match = pattern.search(page)
            if not match:
                pattern = re.compile(
                    rf'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]+'
                    rf'(?:property|name)\s*=\s*["\']{re.escape(name)}["\']',
                    re.I,
                )
                match = pattern.search(page)
            if match:
                return urljoin(final_url, html.unescape(match.group(1).strip()))

        return None

    @staticmethod
    def _download_cover(url: str) -> tuple[bytes, str]:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TangThuStoryScraper/1.0)"
                ),
                "Accept": (
                    "image/avif,image/webp,image/apng,image/svg+xml,"
                    "image/*,*/*;q=0.8"
                ),
            },
        )
        with urlopen(request, timeout=60) as response:
            raw = response.read()
            content_type = str(
                response.headers.get("Content-Type") or ""
            ).lower()

        # Normalize all raster covers to JPEG for broad EPUB-reader
        # compatibility. SVG is converted through Pillow when possible.
        with Image.open(io.BytesIO(raw)) as image:
            image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True)
            return buffer.getvalue(), "image/jpeg"

    @staticmethod
    def _info_html(story: Story) -> str:
        title = html.escape(story.title or story.story_id)
        author = html.escape(story.author or "Không rõ")
        source = html.escape(story.source_url, quote=True)
        registered = (
            str(story.registered_toc_index)
            if story.registered_toc_index is not None
            else "Không xác định"
        )
        return (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            f"<head><title>{title}</title></head><body>"
            f"<h1>{title}</h1>"
            f"<p>Tác giả: {author}</p>"
            f"<p>Tổng mục lục: {len(story.chapters)}</p>"
            f"<p>Vị trí đăng ký: {registered}</p>"
            f'<p><a href="{source}">Nguồn truyện</a></p>'
            "</body></html>"
        )

    @staticmethod
    def _entry_html(story: Story, entry) -> str:
        title = html.escape(entry.title or f"Vị trí {entry.toc_index}")
        url = html.escape(entry.url, quote=True)
        status = html.escape(entry.status.value)
        number = (
            str(entry.number) if entry.number is not None else "—"
        )
        marker = (
            "<p><strong>Vị trí đăng ký hiện tại.</strong></p>"
            if entry.toc_index == story.registered_toc_index
            else ""
        )
        return (
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="vi">'
            f"<head><title>{title}</title></head><body>"
            f"<h1>{entry.toc_index}. {title}</h1>"
            f"<p>Số chương nguồn: {number}</p>"
            f"<p>Loại: {html.escape(entry.kind)}</p>"
            f"<p>Trạng thái: {status}</p>"
            f'<p><a href="{url}">Mở nguồn</a></p>'
            f"{marker}"
            "</body></html>"
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
