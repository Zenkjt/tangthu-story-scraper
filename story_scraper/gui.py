from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .application import build_application
from .core.application_flow import BookshelfStoryFlow, StoryReplacementRequired


class StoryBookshelfGUI:
    """Minimal Tk GUI for Phase 9 bookshelf/story registration flow."""

    def __init__(self, root: tk.Tk, *, user_id: str = "local-user"):
        self.root = root
        self.user_id = user_id
        self.folder = tk.StringVar()
        self.bookshelf_name = tk.StringVar(value="")
        self.story_url = tk.StringVar()
        self.status = tk.StringVar(value="Chưa đăng ký tủ sách")
        self.story_title = tk.StringVar(value="")
        self.reading = tk.StringVar(value="")
        self._story = None
        self._flow: BookshelfStoryFlow | None = None

        self._build()
        self._sync_controls()

    def _build(self):
        self.root.title("Tàng Thư — 0neStory")
        self.root.geometry("760x300")
        self.root.columnconfigure(1, weight=1)

        ttk.Label(self.root, text="Tủ sách:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Label(self.root, textvariable=self.bookshelf_name).grid(row=0, column=1, columnspan=2, sticky="w")

        ttk.Label(self.root, text="Thư mục nhận sách:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(self.root, textvariable=self.folder).grid(row=1, column=1, sticky="ew", padx=4)
        self.register_button = ttk.Button(self.root, text="Đăng ký", command=self.register_folder)
        self.register_button.grid(row=1, column=2, padx=10)

        ttk.Label(self.root, text="Link truyện:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.url_entry = ttk.Entry(self.root, textvariable=self.story_url)
        self.url_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=4)

        self.browse_button = ttk.Button(self.root, text="Duyệt sách", command=self.browse)
        self.browse_button.grid(row=3, column=1, sticky="w", padx=4, pady=10)

        ttk.Separator(self.root).grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
        ttk.Label(self.root, textvariable=self.story_title, font=("TkDefaultFont", 11, "bold")).grid(
            row=5, column=0, columnspan=3, sticky="w", padx=10, pady=5
        )
        ttk.Label(self.root, textvariable=self.reading).grid(row=6, column=0, columnspan=3, sticky="w", padx=10)

        nav = ttk.Frame(self.root)
        nav.grid(row=7, column=0, columnspan=3, sticky="w", padx=10, pady=12)
        self.prev_button = ttk.Button(nav, text="Lùi", command=self.previous)
        self.prev_button.pack(side="left", padx=(0, 6))
        self.next_button = ttk.Button(nav, text="Tiến", command=self.next)
        self.next_button.pack(side="left", padx=6)
        self.jump_button = ttk.Button(nav, text="Nhảy chương", command=self.jump)
        self.jump_button.pack(side="left", padx=6)
        self.get_button = ttk.Button(nav, text="Tải chương", command=self.get_chapter)
        self.get_button.pack(side="left", padx=6)

        ttk.Label(self.root, textvariable=self.status).grid(row=8, column=0, columnspan=3, sticky="w", padx=10)

    def choose_folder(self):
        selected = filedialog.askdirectory(title="Chọn thư mục nhận sách")
        if selected:
            self.folder.set(selected)
            self.register_folder()

    def register_folder(self):
        folder = self.folder.get().strip()
        if not folder:
            self.status.set("Chưa chọn thư mục nhận sách")
            return
        try:
            flow = self._flow_for(folder)
            registration = flow.register_bookshelf(folder)
            self.bookshelf_name.set(registration.name)
            self._load_existing(registration)
            self.status.set(f"Đã đăng ký tủ sách: {registration.name}")
        except Exception as exc:
            messagebox.showerror("Đăng ký thất bại", str(exc))
        self._sync_controls()

    def browse(self):
        folder = self.folder.get().strip()
        if not folder:
            return
        url = self.story_url.get().strip()
        try:
            flow = self._flow_for(folder)
            registration = flow.load_registration(folder)
            if registration is None:
                raise ValueError("Chưa đăng ký tủ sách")

            if registration.story_id and url:
                replacement = messagebox.askyesno(
                    "Đổi truyện",
                    "Bạn muốn đổi sang truyện khác?\nTruyện hiện tại sẽ bị xóa?",
                )
                if not replacement:
                    return
                story = flow.confirm_replace(folder, url)
            else:
                story = flow.browse(folder, url)

            self._show_story(story)
            self.story_url.set("")
            self.status.set("Đã xử lý thành công")
        except StoryReplacementRequired:
            # Defensive fallback; normal GUI path confirms before this point.
            pass
        except Exception as exc:
            messagebox.showerror("Duyệt sách thất bại", str(exc))
        self._sync_controls()

    def previous(self):
        self._navigate(-1)

    def next(self):
        self._navigate(1)

    def _navigate(self, delta: int):
        if self._story is None or self._flow is None:
            return
        numbers = [c.number for c in self._story.chapters]
        current = self._story.target_chapter_number
        if current is None or current not in numbers:
            return
        index = numbers.index(current) + delta
        if 0 <= index < len(numbers):
            self._story = self._flow.set_target(self.folder.get(), numbers[index])
            self._show_story(self._story)

    def jump(self):
        if self._story is None:
            return
        number = simpledialog.askinteger("Nhảy chương", "Số chương:", parent=self.root)
        if number is None:
            return
        try:
            self._story = self._flow.set_target(self.folder.get(), number)
            self._show_story(self._story)
        except Exception as exc:
            messagebox.showerror("Không thể nhảy chương", str(exc))

    def get_chapter(self):
        if self._story is None or self._flow is None:
            return
        try:
            self._story = self._flow.trigger_current(self.folder.get())
            self._show_story(self._story)
            self.status.set("Đã tải chương hiện tại")
        except Exception as exc:
            messagebox.showerror("Tải chương thất bại", str(exc))

    def _load_existing(self, registration):
        if not registration.story_id:
            self._story = None
            self.story_title.set("")
            self.reading.set("")
            return
        try:
            self._story = self._flow.load_current(self.user_id, registration.story_id)
            self._show_story(self._story)
        except FileNotFoundError:
            self._story = None
            self.story_title.set("")
            self.reading.set("")

    def _show_story(self, story):
        self.story_title.set(story.title or story.story_id)
        self.reading.set(f"Đang đọc: Chương {story.target_chapter_number or '—'}")

    def _flow_for(self, folder):
        meta = Path(folder).expanduser().resolve() / ".tangthu"
        app = build_application(
            meta / "state",
            meta / "manifest",
            resolution_root=Path.home() / ".tangthu" / "resolution",
        )
        self._flow = BookshelfStoryFlow(app)
        return self._flow

    def _sync_controls(self):
        registered = bool(self.folder.get().strip() and self._flow is not None)
        state = "normal" if registered else "disabled"
        self.url_entry.configure(state=state)
        self.browse_button.configure(state=state)
        story_ready = registered and self._story is not None
        nav_state = "normal" if story_ready else "disabled"
        self.prev_button.configure(state=nav_state)
        self.next_button.configure(state=nav_state)
        self.jump_button.configure(state=nav_state)
        self.get_button.configure(state=nav_state)


def main():
    root = tk.Tk()
    StoryBookshelfGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
