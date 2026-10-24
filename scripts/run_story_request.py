from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from story_scraper.application import build_application
from story_scraper.core.models import Story
from story_scraper.core.resolution import AdapterResolutionStore
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
        "content": base64.b64encode(
            (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        ).decode("ascii"),
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
    with urlopen(req, timeout=30):
        pass


def read_request(request_id: str) -> dict:
    meta = gh_get(f"contents/story-cache/requests/{request_id}.json?ref=main")
    return json.loads(base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8"))


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value or "")) or "unknown"


def story_view(story: Story) -> dict:
    chapters = sorted(story.chapters, key=lambda c: c.number)
    current = story.target_chapter_number
    current_chapter = next((c for c in chapters if c.number == current), None)
    result = {
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
    }
    if getattr(story, "cover_url", None):
        result["cover_url"] = story.cover_url
    return result


def update_operation(request: dict, status: str, message: str, story: Story | None = None) -> None:
    request["status"] = status
    request["message"] = message
    request["updated_at"] = datetime.now(timezone.utc).isoformat()
    if story is not None:
        request["story_id"] = story.story_id
        request["story"] = story_view(story)
    github_put(
        f"story-cache/requests/{request['request_id']}.json",
        request,
        f"story: {status} {request['request_id']}",
    )


def cache_story(user_id: str, story: Story) -> None:
    github_put(
        f"story-cache/{safe(user_id)}/{safe(story.story_id)}/story.json",
        {
            "schema_version": 1,
            **story.as_dict(),
            "cover_url": getattr(story, "cover_url", None),
        },
        f"story: update cache {user_id}/{story.story_id}",
    )


def hydrate_cached_story(user_id: str, story_id: str) -> Story:
    meta = gh_get(
        f"contents/story-cache/{safe(user_id)}/{safe(story_id)}/story.json?ref=main"
    )
    data = json.loads(base64.b64decode(meta["content"].replace("\n", "")).decode("utf-8"))
    story = Story.from_dict(data)
    if data.get("cover_url"):
        story.cover_url = data["cover_url"]
    return story


def fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=20) as response:
        return response.read().decode(
            response.headers.get_content_charset() or "utf-8",
            errors="replace",
        )


def ensure_cover_url(story: Story) -> None:
    if getattr(story, "cover_url", None):
        return
    html = fetch_text(story.source_url)
    patterns = [
        r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]+content=[\"']([^\"']+)"
        r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"']"
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            story.cover_url = urljoin(story.source_url, match.group(1))
            return
    raise RuntimeError("Không tìm thấy ảnh bìa gốc (og:image).")


def download_cover(story: Story, target: Path) -> None:
    ensure_cover_url(story)
    req = Request(
        story.cover_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)",
            "Referer": story.source_url,
        },
    )
    with urlopen(req, timeout=30) as response:
        target.write_bytes(response.read())


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
        current = {}

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

    payload = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sorted(merged.values(), key=lambda x: x["domain"]),
    }
    github_put(
        "story-cache/story-sources.json",
        payload,
        "story: update source coverage",
    )


class LocalEpubSink:
    def __init__(self, path: Path, cover_path: Path):
        self.sink = StoryEpubSink(path, cover_path)

    def create(self, story):
        self.sink.create(story)

    def append(self, story, chapter, content):
        self.sink.append(story, chapter, content)

    def replace(self, story, chapter, content):
        self.sink.replace(story, chapter, content)


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
            story = app.initialize(user_id, request["url"], _NullSink())
            ensure_cover_url(story)
            cache_story(user_id, story)
            update_operation(request, "completed", "Đăng ký truyện thành công.", story)
            update_source_coverage()
            return 0

        if not story_id:
            raise RuntimeError("Thiếu story_id")

        story = hydrate_cached_story(user_id, story_id)
        # StoryApplication loads runtime state/manifest from its stores on every trigger.
        # Rehydrate both from the persistent GitHub story cache for this ephemeral Action run.
        app.state.save(story)
        app.manifest.save(user_id, story)

        if action == "previous":
            story = app.trigger_previous(user_id, story_id, _NullSink())
            cache_story(user_id, story)
            update_operation(request, "completed", "Đã chuyển về chương trước.", story)
            return 0

        if action == "jump":
            story = app.set_target(user_id, story_id, int(request["chapter_number"]))
            cache_story(user_id, story)
            update_operation(request, "completed", "Đã chọn chương.", story)
            return 0

        if action == "next":
            out = WORK / safe(user_id) / safe(story_id)
            out.mkdir(parents=True, exist_ok=True)
            epub_path = out / "0neStory.epub"
            cover_path = out / "cover.jpg"

            if not download_drive_file(folder_id, "0neStory.epub", epub_path):
                # First chapter request can create the continuous EPUB from scratch.
                download_cover(story, cover_path)
                epub_path.unlink(missing_ok=True)
            elif not cover_path.exists():
                download_cover(story, cover_path)

            story_sink = LocalEpubSink(epub_path, cover_path)
            story = app.trigger_next(user_id, story_id, story_sink)
            cache_story(user_id, story)
            upload_drive(folder_id, "0neStory.epub", epub_path.read_bytes())
            update_operation(request, "completed", "Đã tải/cập nhật chương.", story)
            update_source_coverage()
            return 0

        raise RuntimeError(f"Unsupported action: {action}")

    except Exception as exc:
        try:
            update_operation(request, "failed", str(exc))
        finally:
            update_source_coverage()
        raise


class _NullSink:
    def create(self, story):
        return None

    def append(self, story, chapter, content):
        return None

    def replace(self, story, chapter, content):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
