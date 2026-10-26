from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, Story


class WattpadAdapter(BaseStaticHTMLAdapter):
    name = "wattpad"
    family = "api-story"
    hosts = {"wattpad.com", "www.wattpad.com"}

    API_BASE = "https://www.wattpad.com/api/v3"
    STORYTEXT_BASE = "https://www.wattpad.com/apiv2/"

    _STORY_RE = re.compile(
        r"^/story/(?P<story_id>\d+)(?:-[^/]*)?/?$",
        re.I,
    )

    _PART_RE = re.compile(
        r"^/(?P<part_id>\d+)(?:-[^/]*)?/?$",
        re.I,
    )

    @classmethod
    def matches(cls, url):
        parsed = urlparse(url)

        if cls.host(url) not in cls.hosts:
            return False

        return bool(
            cls._STORY_RE.match(parsed.path)
            or cls._PART_RE.match(parsed.path)
        )

    @classmethod
    def extract_ids(cls, url):
        path = urlparse(url).path

        match = cls._STORY_RE.match(path)
        if match:
            return int(match.group("story_id")), None

        match = cls._PART_RE.match(path)
        if match:
            return None, match.group("part_id")

        return None, None

    @staticmethod
    def _request_json(url):
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TangThuStoryScraper/1.0)"
                )
            },
        )

        with urlopen(req, timeout=30) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    def fetch_story(self, source_url):
        story_id, target_part_id = self.extract_ids(source_url)

        if story_id is None:
            if target_part_id is None:
                raise ValueError(
                    f"Unsupported Wattpad URL: {source_url}"
                )

            part_data = self._request_json(
                f"{self.API_BASE}/story_parts/{target_part_id}"
            )

            story_id = int(part_data["groupId"])

        fields = (
            "id,title,url,user(name,username),"
            "parts(id,title,url,deleted,draft,createDate,modifyDate),"
            "numParts,cover"
        )

        data = self._request_json(
            f"{self.API_BASE}/stories/{story_id}?"
            + urlencode({"fields": fields})
        )

        parts = [
            part
            for part in data.get("parts", [])
            if not part.get("deleted")
            and not part.get("draft")
        ]

        chapters = [
            Chapter(
                number=index,
                title=part.get("title") or f"Chương {index}",
                url=(
                    part.get("url")
                    or f"https://www.wattpad.com/{part['id']}"
                ),
                external_id=str(part["id"]),
            )
            for index, part in enumerate(parts, 1)
        ]

        target = next(
            (
                chapter
                for chapter in chapters
                if chapter.external_id == str(target_part_id)
            ),
            None,
        )

        story = Story(
            story_id=str(data["id"]),
            source_url=source_url,
            site=self.name,
            title=data.get("title", ""),
            author=(data.get("user") or {}).get("name", ""),
            chapters=chapters,
            target_toc_index=(
                target.toc_index if target is not None else 1
            ),
            index_url=data.get("url") or source_url,
        )

        story.normalize_toc()

        if target is not None:
            story.target_toc_index = target.toc_index

        return story

    def build_index(self, url):
        return self.fetch_story(url)

    def refresh_index(self, story: Story) -> Story:
        return self.fetch_story(story.source_url)

    def refresh_tail(self, story):
        refreshed = self.refresh_index(story)

        known = {
            chapter.external_id
            for chapter in story.chapters
            if chapter.external_id
        }

        return [
            chapter
            for chapter in refreshed.chapters
            if chapter.external_id not in known
        ]

def _fetch_storytext(self, chapter_id: str) -> str:
    url = (
        self.STORYTEXT_BASE
        + "?"
        + urlencode(
            {
                "m": "storytext",
                "id": chapter_id,
            }
        )
    )

    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; TangThuStoryScraper/1.0)"
            )
        },
    )

    with urlopen(req, timeout=30) as response:
        raw = response.read()

        content_type = response.headers.get("Content-Type", "")
        content_encoding = response.headers.get("Content-Encoding", "")
        content_length = response.headers.get("Content-Length", "")

    print("=== WATTPAD RAW DEBUG ===")
    print(f"chapter_id={chapter_id}")
    print(f"status=200")
    print(f"content-type={content_type}")
    print(f"content-encoding={content_encoding}")
    print(f"content-length={content_length}")
    print(f"raw-length={len(raw)}")
    print(f"first-64-bytes-hex={raw[:64].hex()}")
    print("=========================")

    debug_path = "wattpad_raw_debug.bin"

    with open(debug_path, "wb") as debug_file:
        debug_file.write(raw)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Wattpad raw storytext is not valid UTF-8. "
            f"Raw response saved to {debug_path}. "
            f"Decode error: {exc}"
        ) from exc

    if not text.strip():
        raise ValueError(
            f"Wattpad chapter {chapter_id} returned empty text"
        )

    return text
    
    def fetch_chapter(self, chapter):
        if not chapter.external_id:
            raise ValueError(
                "Wattpad chapter is missing external_id"
            )

        html = self._fetch_storytext(
            chapter.external_id
        )

        soup = self.soup(html)

        return (
            self.extract_images(
                soup.body or soup,
                chapter.url,
                prefix=f"chapter-{chapter.number}",
            ),
            True,
        )
        
