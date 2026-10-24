from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from .core.bookshelf import BookshelfBackend, BookshelfRegistration
from .core.application_flow import BookshelfWriteError, StoryRegistrationFlow
from .application import build_application


class Bulletin:
    """Persistent notification panel. It never auto-closes."""

    def __init__(self, parent: tk.Misc):
        self.window = tk.Toplevel(parent)
        self.window.title("Bảng tin")
        self.window.geometry("560x260")
        self.window.resizable(True, True)
        self.window.transient(parent)

        header = ttk.Frame(self.window)
        header.pack(fill="x", padx=8, pady=8)
        ttk.Label(header, text="BẢNG TIN", font=("TkDefaultFont", 11, "bold")).pack(
            side="left"
        )
        ttk.Button(header, text="X", width=3, command=self.window.destroy).pack(
            side="right"
        )

        body = ttk.Frame(self.window)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.text = tk.Text(body, wrap="word", state="disabled")
        scroll = ttk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def add(self, message: str):
        self.text.configure(state="normal")
        self.text.insert("end", f"• {message}\n\n")
        self.text.see("end")
        self.text.configure(state="disabled")


class StoryBookshelfGUI:
    """Phase 9 desktop GUI.

    No bookshelf registration state is stored in the user's Drive folder.
    """

    def __init__(
        self,
        root: tk.Tk,
        *,
        bookshelf_backend: BookshelfBackend,
        state_root,
        manifest_root,
        resolution_root,
        artifact_root,
        cover_path,
    ):
        self.root = root
        self.backend = bookshelf_backend
        self.bulletin: Bulletin | None = None
        self.registration: BookshelfRegistration | None = None
        self.story = None

        self.folder_url = tk.StringVar()
        self.story_url = tk.StringVar()
        self.info = tk.StringVar(value="Chưa đăng ký nội dung đọc")
        self.shelf_info = tk.StringVar(value="")
        self.chapter_info = tk.StringVar(value="")
        self._flow = StoryRegistrationFlow(
            build_application(
                state_root,
                manifest_root,
                resolution_root=resolution_root,
            ),
            bookshelf_backend,
            artifact_root,
            cover_path,
            notify=self._notify,
        )

        self._build()
        self._sync()

    def _build(self):
        self.root.title("Đăng ký đọc online")
        self.root.geometry("760x620")
        self.root.minsize(650, 500)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=10, pady=8)
        ttk.Button(toolbar, text="?", width=3, command=self._help).pack(side="right")
        ttk.Button(toolbar, text="X", width=3, command=self.root.destroy).pack(side="right", padx=(6, 0))
        ttk.Label(toolbar, text="Đăng ký đọc online", font=("TkDefaultFont", 13, "bold")).pack(side="left")

        info_box = ttk.LabelFrame(self.root, text="THÔNG TIN")
        info_box.pack(fill="x", padx=10, pady=6)
        ttk.Label(info_box, textvariable=self.info, justify="left", wraplength=700).pack(
            fill="x", padx=10, pady=10
        )
        ttk.Label(info_box, textvariable=self.shelf_info, justify="left").pack(
            fill="x", padx=10, pady=(0, 8)
        )
        ttk.Label(info_box, textvariable=self.chapter_info).pack(
            fill="x", padx=10, pady=(0, 10)
        )

        nav = ttk.Frame(self.root)
        nav.pack(fill="x", padx=10, pady=8)
        self.prev_btn = ttk.Button(nav, text="< Chương trước", command=lambda: self._move(-1))
        self.prev_btn.pack(side="left")
        self.jump = ttk.Combobox(nav, width=18, state="disabled")
        self.jump.pack(side="left", padx=8)
        self.jump.bind("<<ComboboxSelected>>", self._jump)
        self.next_btn = ttk.Button(nav, text="Chương sau >", command=lambda: self._move(1))
        self.next_btn.pack(side="left")

        story_box = ttk.LabelFrame(self.root, text="Link truyện")
        story_box.pack(fill="x", padx=10, pady=6)
        row = ttk.Frame(story_box)
        row.pack(fill="x", padx=8, pady=8)
        self.story_entry = ttk.Entry(row, textvariable=self.story_url)
        self.story_entry.pack(side="left", fill="x", expand=True)
        self.register_btn = ttk.Button(row, text="Đăng ký", command=self._register_story)
        self.register_btn.pack(side="left", padx=(8, 0))

        shelf_box = ttk.LabelFrame(self.root, text="Thư mục nhận sách")
        shelf_box.pack(fill="x", padx=10, pady=6)
        self.folder_entry = ttk.Entry(shelf_box, textvariable=self.folder_url)
        self.folder_entry.pack(fill="x", padx=8, pady=8)
        self.folder_entry.bind("<KeyRelease>", self._folder_changed)

    def _notify(self, message: str):
        def update():
            if self.bulletin is None or not self.bulletin.window.winfo_exists():
                self.bulletin = Bulletin(self.root)
            self.bulletin.add(message)
        self.root.after(0, update)

    def _folder_changed(self, _event=None):
        url = self.folder_url.get().strip()
        self.registration = None
        self.info.set("Đang kiểm tra tủ nhận sách..." if url else "Chưa đăng ký nội dung đọc")
        self._sync()
        if not url:
            return

        def worker():
            try:
                registration = self.backend.inspect(url)
            except Exception as exc:
                self.root.after(0, lambda: self._folder_error(str(exc)))
                return
            self.root.after(0, lambda: self._folder_result(registration))

        threading.Thread(target=worker, daemon=True).start()

    def _folder_result(self, registration):
        self.registration = registration
        if registration is None:
            self.info.set(
                "Không có thông tin tủ. Yêu cầu lập tủ sách để nhận sách."
            )
        else:
            permission = (
                " · quyền ghi: có"
                if registration.can_edit is True
                else " · quyền ghi: chưa xác định"
                if registration.can_edit is None
                else " · quyền ghi: không có"
            )
            self.info.set(f"Đã nhận ra tủ: {registration.name}{permission}")
            self.shelf_info.set(
                f"Tủ nhận sách: {registration.name} · "
                "0neStory.epub · 0neStoryTOC.epub"
            )
        self._sync()

    def _folder_error(self, message):
        self.registration = None
        self.info.set(f"Không thể kiểm tra tủ nhận sách: {message}")
        self._sync()

    def _register_story(self):
        if self.registration is None:
            self._notify(
                "Chưa có tủ nhận sách. Hãy đăng ký tủ sách Tàng Thư trước."
            )
            return
        url = self.story_url.get().strip()
        if not url:
            self._notify("Chưa nhập link truyện.")
            return

        self.register_btn.configure(state="disabled")
        self._notify("Đang scrape và đăng ký truyện...")

        def worker():
            try:
                story = self._flow.register_story(self.registration, url)
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self._registration_error(exc))
                return
            self.root.after(0, lambda: self._registration_done(story))

        threading.Thread(target=worker, daemon=True).start()

    def _registration_error(self, message):
        if isinstance(message, BookshelfWriteError):
            self._notify(str(message))
        else:
            self._notify(f"Scrape/đăng ký thất bại: {message}")
        self.register_btn.configure(state="normal")

    def _registration_done(self, story):
        self.story = story
        self._render_story()
        self.register_btn.configure(state="normal")
        self._sync()

    def _render_story(self):
        if self.story is None:
            return
        current = self.story.target_chapter_number
        self.info.set(
            f"{self.story.title or self.story.story_id}\n"
            f"Tác giả: {self.story.author or '—'}\n"
            f"Nguồn: {self.story.source_url}"
        )
        self.chapter_info.set(
            f"Chương hiện tại: {current or '—'} · "
            f"Tổng đã biết: {len(self.story.chapters)}"
        )
        self.jump["values"] = [
            f"{c.number}: {c.title}" for c in self.story.chapters
        ]
        if current is not None:
            for value in self.jump["values"]:
                if value.startswith(f"{current}:"):
                    self.jump.set(value)
                    break

    def _move(self, delta: int):
        if self.story is None:
            return
        numbers = [c.number for c in self.story.chapters]
        current = self.story.target_chapter_number
        if current not in numbers:
            return
        index = numbers.index(current) + delta
        if not 0 <= index < len(numbers):
            return
        target = numbers[index]
        self.story = self._flow.set_target(self.story.story_id, target)
        self._render_story()
        self._notify(f"Đã chuyển mục tiêu sang chương {target}.")
        self._fetch_current()

    def _jump(self, _event=None):
        if self.story is None:
            return
        value = self.jump.get().split(":", 1)[0]
        if not value.isdigit():
            return
        target = int(value)
        self.story = self._flow.set_target(self.story.story_id, target)
        self._render_story()
        self._notify(f"Đã chuyển mục tiêu sang chương {target}.")
        self._fetch_current()

    def _fetch_current(self):
        if self.registration is None or self.story is None:
            return
        try:
            self.story = self._flow.trigger_current(
                self.registration,
                self.story.story_id,
            )
            self._render_story()
        except Exception as exc:
            self._notify(f"Tải chapter thất bại: {exc}")

    def _help(self):
        self._notify(
            "Dán link tủ sách trước. Sau khi nhận ra tủ, nhập link truyện và bấm Đăng ký."
        )

    def _sync(self):
        enabled = self.registration is not None
        self.story_entry.configure(state="normal" if enabled else "disabled")
        self.register_btn.configure(state="normal" if enabled else "disabled")
        story_ready = self.story is not None
        self.prev_btn.configure(state="normal" if story_ready else "disabled")
        self.next_btn.configure(state="normal" if story_ready else "disabled")
        self.jump.configure(state="readonly" if story_ready else "disabled")


def main():
    raise SystemExit(
        "GUI requires an injected BookshelfBackend; use StoryBookshelfGUI(...) from an integration entry point."
    )


if __name__ == "__main__":
    main()
