from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from story_scraper.application import build_application
from story_scraper.core.models import Story
from story_scraper.core.resolution import AdapterResolutionStore
from story_scraper.story_catalog import StoryCatalogEpubSink
from story_scraper.story_epub import StoryEpubSink

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".story-work"
STATE_ROOT = WORK / "state"
MANIFEST_ROOT = WORK / "manifest"
RESOLUTION_ROOT = WORK / "resolution.jsonl"


def gh_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TangThu-Story-Action/1.0",
    }


def gh_get(path: str) -> dict:
    req = Request(
        f"https://api.github.com/repos/Zenkjt/tangthu-story-scraper/{path}",
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
    api = f"https://api.github.com/repos/Zenkjt/tangthu-story-scraper/contents/{path}"
    sha = None
    try:
        req = Request(api + "?ref=main", headers=gh_headers())
        with urlopen(req, timeout=30) as response:
            sha = json.loads(response.read().decode("utf-8"))["sha"]
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


def read_request(request_id: str) -> dict:
    meta = gh_get(f"contents/story-cache/requests/{request_id}.json?ref=main")
    return json.loads(
        base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8")
    )


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value or "")) or "unknown"


def fetch_cover(source_url: str) -> tuple[bytes, str] | None:
    """Best-effort GUI cover discovery. Cover is cache/UI metadata, never EPUB content."""
    try:
        request = Request(
            source_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        with urlopen(request, timeout=30) as response:
            html = response.read().decode(
                response.headers.get_content_charset() or "utf-8",
                errors="replace",
            )
        match = re.search(
            r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
                html,
                flags=re.I,
            )
        if not match:
            return None
        cover_url = match.group(1).strip()
        cover_request = Request(
            cover_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)",
                "Referer": source_url,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
        )
        with urlopen(cover_request, timeout=60) as response:
            payload = response.read()
            media_type = response.headers.get_content_type() or "image/jpeg"
        ext = {
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/jpeg": ".jpg",
        }.get(media_type, ".jpg")
        return payload, ext
    except Exception:
        return None


def cover_cache_url(user_id: str, story_id: str, ext: str = ".jpg") -> str:
    return (
        "https://raw.githubusercontent.com/Zenkjt/tangthu-story-scraper/"
        f"main/story-cache/{safe(user_id)}/{safe(story_id)}/cover{ext}"
    )


def story_view(story: Story, user_id: str | None = None, cover_ext: str = ".jpg") -> dict:
    chapters = sorted(story.chapters, key=lambda c: c.number)
    current = story.target_chapter_number
    current_chapter = next((c for c in chapters if c.number == current), None)
    return {
        "story_id": story.story_id,
        "title": story.title,
        "author": story.author,
        "site": story.site,
        "source_url": story.source_url,
        "current_chapter": current,
        "current_chapter_title": current_chapter.title if current_chapter else None,
        "total_chapters": len(chapters),
        "chapters": [
            {
                "number": c.number,
                "title": c.title,
                "url": c.url,
                "status": c.status.value,
            }
            for c in chapters
        ],
        "status": "ready",
        "cover_url": (
            cover_cache_url(user_id, story.story_id, cover_ext)
            if user_id
            else None
        ),
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
        request["story"] = story_view(
            story,
            request.get("user_id"),
            request.get("cover_ext", ".jpg"),
        )
    github_put(
        f"story-cache/requests/{request['request_id']}.json",
        request,
        f"story: {status} {request['request_id']}",
    )


def cache_story(
    user_id: str,
    story: Story,
    *,
    cover_ext: str | None = None,
) -> None:
    data = {"schema_version": 1, **story.as_dict()}
    if cover_ext:
        data["cover_ext"] = cover_ext
        data["cover_url"] = cover_cache_url(user_id, story.story_id, cover_ext)
    github_put(
        f"story-cache/{safe(user_id)}/{safe(story.story_id)}/story.json",
        data,
        f"story: update cache {user_id}/{story.story_id}",
    )
    github_put(
        f"story-cache/{safe(user_id)}/current.json",
        {
            "schema_version": 1,
            "story_id": story.story_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        f"story: set current {user_id}/{story.story_id}",
    )


def hydrate_cached_story(user_id: str, story_id: str) -> Story:
    meta = gh_get(
        f"contents/story-cache/{safe(user_id)}/{safe(story_id)}/story.json?ref=main"
    )
    data = json.loads(
        base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8")
    )
    return Story.from_dict(data)


def drive_files(folder_id: str) -> list[dict]:
    key = os.environ["TANGTHU_GOOGLE_API_KEY"]
    q = quote(f"'{folder_id}' in parents and trashed = false")
    fields = quote("files(id,name,size,mimeType,webContentLink)")
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q={q}&fields={fields}&pageSize=100&key={quote(key)}"
    )
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")).get("files", [])


def download_drive_file(folder_id: str, filename: str, target: Path) -> bool:
    files = [f for f in drive_files(folder_id) if f.get("name") == filename]
    if not files:
        return False
    if len(files) > 1:
        raise RuntimeError(f"Drive có nhiều file {filename}; từ chối chọn mơ hồ.")

    file_id = files[0]["id"]
    key = os.environ["TANGTHU_GOOGLE_API_KEY"]
    url = (
        f"https://www.googleapis.com/drive/v3/files/{quote(file_id, safe='')}"
        f"?alt=media&key={quote(key)}"
    )
    req = Request(url, headers={"User-Agent": "TangThu-Story-Action/1.0"})
    with urlopen(req, timeout=120) as response:
        target.write_bytes(response.read())
    return True


def upload_drive(folder_id: str, filename: str, payload: bytes) -> None:
    url = os.environ["TANGTHU_APPS_SCRIPT_URL"]
    body = {
        "action": "upload_epub",
        "token": os.environ["TANGTHU_UPLOAD_TOKEN"],
        "folder_id": folder_id,
        "filename": filename,
        "mime_type": "application/epub+zip",
        "content_base64": base64.b64encode(payload).decode("ascii"),
    }
    req = Request(
        url,
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
        meta = gh_get("contents/story-cache/story-sources.json?ref=main")
        current = json.loads(
            base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8")
        )
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
            "message": (
                "Bình thường"
                if item.status == "good"
                else (item.reason or "Không truy cập được")
            ),
        }

    github_put(
        "story-cache/story-sources.json",
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


def main() -> int:
    request = read_request(os.environ["STORY_REQUEST_ID"])
    action = request["action"]
    user_id = request["user_id"]
    story_id = request.get("story_id")
    folder_id = request["folder_id"]

    try:
        update_operation(request, "running", f"Đang xử lý: {action}.")
        WORK.mkdir(parents=True, exist_ok=True)

        app = build_application(
            STATE_ROOT,
            MANIFEST_ROOT,
            resolution_root=RESOLUTION_ROOT,
        )

        if action == "register":
            story = app.registry.resolve_source(request["url"]).story

            out = WORK / safe(user_id) / safe(story.story_id)
            out.mkdir(parents=True, exist_ok=True)

            catalog_path = out / "0neStoryTOC.epub"
            catalog = StoryCatalogEpubSink(catalog_path)

            story = app.initialize(
                user_id,
                request["url"],
                _NullSink(),
                catalog=catalog,
            )

            cover_ext = ".jpg"
            cover = fetch_cover(story.source_url)
            if cover:
                cover_bytes, cover_ext = cover
                github_put_bytes(
                    f"story-cache/{safe(user_id)}/{safe(story.story_id)}/cover{cover_ext}",
                    cover_bytes,
                    f"story: cache cover {user_id}/{story.story_id}",
                )

            cache_story(user_id, story, cover_ext=cover_ext if cover else None)
            upload_drive(
                folder_id,
                "0neStoryTOC.epub",
                catalog_path.read_bytes(),
            )

            request["cover_ext"] = cover_ext if cover else ".jpg"
            update_operation(
                request,
                "completed",
                "Đăng ký truyện thành công.",
                story,
            )
            update_source_coverage()
            return 0

        if not story_id:
            raise RuntimeError("Thiếu story_id")

        story = hydrate_cached_story(user_id, story_id)
        app.state.save(story)
        app.manifest.save(user_id, story)

        if action == "previous":
            story = app.trigger_previous(user_id, story_id, _NullSink())
            cache_story(user_id, story)
            update_operation(
                request,
                "completed",
                "Đã chuyển về chương trước.",
                story,
            )
            return 0

        if action == "jump":
            story = app.set_target(
                user_id,
                story_id,
                int(request["chapter_number"]),
            )
            cache_story(user_id, story)
            update_operation(
                request,
                "completed",
                "Đã chọn chương.",
                story,
            )
            return 0

        if action == "next":
            out = WORK / safe(user_id) / safe(story_id)
            out.mkdir(parents=True, exist_ok=True)
            epub_path = out / "0neStory.epub"

            if not download_drive_file(folder_id, "0neStory.epub", epub_path):
                epub_path.unlink(missing_ok=True)

            story_sink = LocalEpubSink(epub_path)
            story = app.trigger_next(
                user_id,
                story_id,
                story_sink,
            )

            cache_story(user_id, story)
            upload_drive(
                folder_id,
                "0neStory.epub",
                epub_path.read_bytes(),
            )

            update_operation(
                request,
                "completed",
                "Đã tải/cập nhật chương.",
                story,
            )
            update_source_coverage()
            return 0

        raise RuntimeError(f"Unsupported action: {action}")

    except Exception as exc:
        update_operation(request, "failed", str(exc))
        update_source_coverage()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
