from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from story_scraper.application import build_application
from story_scraper.core.models import Story
from story_scraper.core.registry import ResolvedStorySource
from story_scraper.core.resolution import AdapterResolutionStore
from story_scraper.story_catalog import StoryCatalogEpubSink
from story_scraper.story_epub import StoryEpubSink
from story_shelf_cache import (
    ShelfCachedAdapter,
    ensure_story_cache,
    read_story_state,
    write_story_state,
)

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".story-work"
STATE_ROOT = WORK / "state"
MANIFEST_ROOT = WORK / "manifest"
RESOLUTION_ROOT = WORK / "resolution.jsonl"

REPO = "Zenkjt/tangthu-story-scraper"
CONTROL_ROOT = "story-cache"


def gh_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TangThu-Story-Action/1.0",
    }


def gh_get(path: str) -> dict:
    req = Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        headers=gh_headers(),
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def github_put(path: str, payload: dict, message: str) -> None:
    github_put_bytes(
        path,
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        message,
    )


def github_put_bytes(path: str, content: bytes, message: str) -> None:
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    sha = None
    try:
        meta = gh_get(f"contents/{path}?ref=main")
        sha = meta.get("sha")
    except Exception:
        pass

    body = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    req = Request(
        api,
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
        headers={**gh_headers(), "Content-Type": "application/json"},
    )
    with urlopen(req, timeout=60):
        pass


def read_control_json(path: str) -> dict:
    meta = gh_get(f"contents/{path}?ref=main")
    return json.loads(
        base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8")
    )


def read_request(request_id: str) -> dict:
    return read_control_json(f"{CONTROL_ROOT}/requests/{request_id}.json")


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value or "")) or "unknown"


def normalize_url(value: str | None) -> str:
    return str(value or "").strip().rstrip("/")


def find_registered_toc_index(story: Story, source_url: str) -> int:
    requested = normalize_url(source_url)
    matches = [
        entry.toc_index
        for entry in story.chapters
        if normalize_url(entry.url) == requested
    ]
    if len(matches) == 1:
        return matches[0]

    story_urls = {
        normalize_url(story.source_url),
        normalize_url(story.index_url),
    }
    if requested in story_urls:
        return story.target_toc_index or story.chapters[0].toc_index

    raise RuntimeError(
        "Không xác định được chính xác vị trí đăng ký trong TOC "
        f"từ URL: {source_url}"
    )


def story_view(story: Story) -> dict:
    story.normalize_toc()
    current = story.current_toc_index
    current_entry = story.entry_at(current)
    return {
        "story_id": story.story_id,
        "title": story.title,
        "author": story.author,
        "site": story.site,
        "source_url": story.source_url,
        "current_toc_index": current,
        "target_toc_index": story.target_toc_index,
        "registered_toc_index": story.registered_toc_index,
        "current_chapter": current,
        "current_chapter_title": current_entry.title if current_entry else None,
        "total_toc_entries": len(story.chapters),
        "total_chapters": len(story.chapters),
        "chapters": [
            {
                "toc_index": entry.toc_index,
                "number": entry.number,
                "title": entry.title,
                "url": entry.url,
                "kind": entry.kind,
                "status": entry.status.value,
            }
            for entry in story.chapters
        ],
        "status": "ready",
        "cover_url": story.cover_url,
    }


def update_operation(
    request: dict,
    status: str,
    message: str,
    story: Story | None = None,
) -> None:
    request["status"] = status
    request["message"] = message
    request["updated_at"] = datetime.now(timezone.utc).isoformat()
    if story is not None:
        request["story_id"] = story.story_id
        request["story"] = story_view(story)
    github_put(
        f"{CONTROL_ROOT}/requests/{request['request_id']}.json",
        request,
        f"story: {status} {request['request_id']}",
    )


def extract_meta(html: str, name: str) -> str | None:
    patterns = [
        rf'<meta[^>]+(?:property|name)\s*=\s*["\']{re.escape(name)}["\'][^>]+content\s*=\s*["\']([^"\']+)',
        rf'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]+(?:property|name)\s*=\s*["\']{re.escape(name)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return unescape(match.group(1).strip())
    return None


def ensure_cover_url(story: Story) -> None:
    if story.cover_url:
        return
    try:
        request = Request(
            story.source_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")
            final_url = response.geturl()
        for key in ("og:image", "twitter:image", "twitter:image:src"):
            value = extract_meta(html, key)
            if value:
                story.cover_url = urljoin(final_url, value)
                return
    except Exception as exc:
        print(f"Cover: không lấy được bìa, bỏ qua: {exc}")


def upload_drive(folder_id: str, filename: str, payload: bytes) -> None:
    body = {
        "action": "upload_epub",
        "token": os.environ["TANGTHU_UPLOAD_TOKEN"],
        "folder_id": folder_id,
        "filename": filename,
        "mime_type": "application/epub+zip",
        "content_base64": base64.b64encode(payload).decode("ascii"),
    }
    req = Request(
        os.environ["TANGTHU_APPS_SCRIPT_URL"],
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Drive upload thất bại"))


def update_source_coverage() -> None:
    store = AdapterResolutionStore(RESOLUTION_ROOT)
    current = {}
    try:
        current = read_control_json(f"{CONTROL_ROOT}/story-sources.json")
    except Exception:
        pass

    merged = {
        str(item.get("domain")): item
        for item in current.get("sources", [])
        if item.get("domain")
    }
    for item in store.active_coverage():
        merged[item.domain] = {
            "domain": item.domain,
            "status": "ok" if item.status == "good" else "fail",
            "adapter": item.adapter,
            "reason": item.reason,
            "timestamp": item.timestamp,
            "message": "Bình thường" if item.status == "good" else (item.reason or "Không truy cập được"),
        }

    github_put(
        f"{CONTROL_ROOT}/story-sources.json",
        {
            "schema_version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "sources": sorted(merged.values(), key=lambda x: x["domain"]),
        },
        "story: update source coverage",
    )


class LocalEpubSink:
    def __init__(self, path: Path):
        self.sink = StoryEpubSink(path)

    def create(self, story):
        self.sink.create(story)

    def append(self, story, chapter, content):
        self.sink.append(story, chapter, content)

    def replace(self, story, chapter, content):
        self.sink.replace(story, chapter, content)


class _NullSink:
    def create(self, story):
        return None

    def append(self, story, chapter, content):
        return None

    def replace(self, story, chapter, content):
        return None


def toc_signature(story: Story):
    story.normalize_toc()
    return tuple(
        (
            entry.toc_index,
            entry.number,
            entry.title,
            normalize_url(entry.url),
            entry.external_id,
            entry.kind,
        )
        for entry in story.chapters
    )


def install_cached_registry(app, folder_id: str, story_id: str) -> None:
    """Make every later registry-created adapter shelf-cache aware.

    StoryApplication.trigger_next()/previous() resolve a fresh adapter through
    registry.resolve_instance(), so this hook is required. We do not mutate the
    adapter registry globally outside this request.
    """
    original = app.registry.resolve_instance

    def resolve_instance(url: str):
        return ShelfCachedAdapter(original(url), folder_id, story_id)

    app.registry.resolve_instance = resolve_instance


def build_cached_source(app, url: str, folder_id: str, story_id: str):
    resolved = app.registry.resolve_source(url)
    return ResolvedStorySource(
        ShelfCachedAdapter(resolved.adapter, folder_id, story_id),
        resolved.story,
    )


def main() -> int:
    request = read_request(os.environ["STORY_REQUEST_ID"])
    action = request["action"]
    user_id = request["user_id"]
    story_id = request.get("story_id")
    folder_id = str(request["folder_id"])

    try:
        update_operation(request, "running", f"Đang xử lý: {action}.")
        WORK.mkdir(parents=True, exist_ok=True)

        app = build_application(
            STATE_ROOT,
            MANIFEST_ROOT,
            resolution_root=RESOLUTION_ROOT,
        )

        if action == "register":
            resolved = app.registry.resolve_source(request["url"])
            story = resolved.story
            story.normalize_toc()
            registered_toc_index = find_registered_toc_index(story, request["url"])
            ensure_cover_url(story)
            ensure_story_cache(folder_id, story.story_id)

            cached_source = ResolvedStorySource(
                ShelfCachedAdapter(resolved.adapter, folder_id, story.story_id),
                story,
            )
            install_cached_registry(app, folder_id, story.story_id)

            out = WORK / safe(user_id) / safe(story.story_id)
            out.mkdir(parents=True, exist_ok=True)
            story_path = out / "0neStory.epub"
            catalog_path = out / "0neStoryTOC.epub"
            catalog = StoryCatalogEpubSink(catalog_path)
            story_sink = LocalEpubSink(story_path)

            story = app.initialize(
                user_id,
                request["url"],
                story_sink,
                start_toc_index=registered_toc_index,
                catalog=catalog,
                resolved_source=cached_source,
            )
            story = app.trigger_next(
                user_id,
                story.story_id,
                story_sink,
                catalog=catalog,
            )

            write_story_state(folder_id, story)

            if not story_path.exists() or not catalog_path.exists():
                raise RuntimeError("Không tạo đủ 0neStory.epub / 0neStoryTOC.epub.")

            upload_drive(folder_id, "0neStoryTOC.epub", catalog_path.read_bytes())
            upload_drive(folder_id, "0neStory.epub", story_path.read_bytes())

            update_operation(request, "completed", "Đăng ký truyện thành công.", story)
            update_source_coverage()
            return 0

        if not story_id:
            raise RuntimeError("Thiếu story_id")

        state = read_story_state(folder_id, story_id)
        if state is None:
            raise RuntimeError(
                f"Không tìm thấy StoryState trong tủ sách cho story_id={story_id}."
            )

        story = Story.from_dict(state["story"])
        app.state.save(story)
        app.manifest.save(user_id, story)
        install_cached_registry(app, folder_id, story.story_id)

        out = WORK / safe(user_id) / safe(story_id)
        out.mkdir(parents=True, exist_ok=True)
        story_path = out / "0neStory.epub"
        catalog_path = out / "0neStoryTOC.epub"
        catalog = StoryCatalogEpubSink(catalog_path)

        if action == "previous":
            story = app.trigger_previous(
                user_id,
                story_id,
                _NullSink(),
                catalog=catalog,
            )
            write_story_state(folder_id, story)
            update_operation(
                request,
                "completed",
                "Đã chuyển về vị trí trước trong mục lục.",
                story,
            )
            return 0

        if action == "jump":
            toc_index = int(request.get("toc_index", request.get("chapter_number", 0)))
            if toc_index < 1:
                raise ValueError("TOC position must be >= 1")

            story = app.set_target(user_id, story_id, toc_index)
            requested_entry = story.entry_at(toc_index)
            if requested_entry is None:
                raise ValueError(f"Unknown TOC position: {toc_index}")
            requested_identity = (
                requested_entry.external_id,
                normalize_url(requested_entry.url),
                requested_entry.kind,
            )
            before = toc_signature(story)

            story_sink = LocalEpubSink(story_path)
            story = app.trigger_next(
                user_id,
                story_id,
                story_sink,
                catalog=catalog,
            )
            after = toc_signature(story)

            fetched_entry = next(
                (
                    entry
                    for entry in story.chapters
                    if (
                        entry.external_id,
                        normalize_url(entry.url),
                        entry.kind,
                    )
                    == requested_identity
                ),
                None,
            )
            if fetched_entry is None:
                raise RuntimeError(
                    f"Không còn tìm thấy vị trí TOC {toc_index} sau khi tải."
                )
            story = app.set_target(user_id, story_id, fetched_entry.toc_index)
            write_story_state(folder_id, story)

            if not story_path.exists():
                raise RuntimeError("Không tạo được 0neStory.epub cho vị trí yêu cầu.")
            upload_drive(folder_id, "0neStory.epub", story_path.read_bytes())
            if before != after and catalog_path.exists():
                upload_drive(folder_id, "0neStoryTOC.epub", catalog_path.read_bytes())

            update_operation(
                request,
                "completed",
                f"Đã tải vị trí {toc_index} trong mục lục.",
                story,
            )
            update_source_coverage()
            return 0

        if action == "next":
            before = toc_signature(story)
            story_sink = LocalEpubSink(story_path)
            story = app.trigger_next(
                user_id,
                story_id,
                story_sink,
                catalog=catalog,
            )
            after = toc_signature(story)
            write_story_state(folder_id, story)

            if not story_path.exists():
                raise RuntimeError("Không tạo được 0neStory.epub cho vị trí tiếp theo.")
            upload_drive(folder_id, "0neStory.epub", story_path.read_bytes())
            if before != after and catalog_path.exists():
                upload_drive(folder_id, "0neStoryTOC.epub", catalog_path.read_bytes())

            message = (
                "Đã tải nội dung và cập nhật mục lục."
                if before != after
                else "Đã tải nội dung."
            )
            update_operation(request, "completed", message, story)
            update_source_coverage()
            return 0

        raise RuntimeError(f"Unsupported action: {action}")

    except Exception as exc:
        update_operation(request, "failed", str(exc))
        try:
            update_source_coverage()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
