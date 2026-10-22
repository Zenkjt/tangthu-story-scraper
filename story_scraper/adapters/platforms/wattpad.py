from __future__ import annotations
import json, re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from ...core.html_adapter import BaseStaticHTMLAdapter
from ...core.models import Chapter, ChapterContent, Story

class WattpadAdapter(BaseStaticHTMLAdapter):
    name="wattpad"
    family="api-story"
    hosts={"wattpad.com","www.wattpad.com"}
    API_BASE="https://www.wattpad.com/api/v3"
    STORYTEXT_BASE="https://www.wattpad.com/apiv2/storytext"
    _STORY_RE=re.compile(r"^/story/(?P<story_id>\d+)(?:-[^/]*)?/?$",re.I)
    _PART_RE=re.compile(r"^/(?P<part_id>\d+)(?:-[^/]*)?/?$",re.I)

    @classmethod
    def matches(cls,url):
        return cls.host(url) in cls.hosts and bool(cls._STORY_RE.match(urlparse(url).path) or cls._PART_RE.match(urlparse(url).path))

    @classmethod
    def extract_ids(cls,url):
        path=urlparse(url).path
        m=cls._STORY_RE.match(path)
        if m: return int(m.group("story_id")),None
        m=cls._PART_RE.match(path)
        if m: return None,m.group("part_id")
        return None,None

    @staticmethod
    def _request_json(url):
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; TangThuStoryScraper/1.0)"})
        with urlopen(req,timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_story(self,source_url):
        story_id,target_part_id=self.extract_ids(source_url)
        if story_id is None:
            if target_part_id is None: raise ValueError(f"Unsupported Wattpad URL: {source_url}")
            story_id=int(self._request_json(f"{self.API_BASE}/story_parts/{target_part_id}")["groupId"])
        fields="id,title,url,user(name,username),parts(id,title,url,deleted,draft,createDate,modifyDate),numParts,cover"
        data=self._request_json(f"{self.API_BASE}/stories/{story_id}?"+urlencode({"fields":fields}))
        parts=[p for p in data.get("parts",[]) if not p.get("deleted") and not p.get("draft")]
        chapters=[Chapter(number=n,title=p.get("title") or f"Chương {n}",url=p.get("url") or f"https://www.wattpad.com/{p['id']}",external_id=str(p["id"])) for n,p in enumerate(parts,1)]
        target=next((c.number for c in chapters if c.external_id==str(target_part_id)),None)
        return Story(str(data["id"]),source_url,self.name,data.get("title",""),(data.get("user") or {}).get("name",""),chapters,target if target is not None else (chapters[0].number if chapters else None))

    def build_index(self,url):
        return self.fetch_story(url)

    def fetch_chapter(self,chapter):
        if not chapter.external_id: raise ValueError("Wattpad chapter is missing external_id")
        html=self.fetch_html(f"{self.STORYTEXT_BASE}?"+urlencode({"id":chapter.external_id}))
        soup=self.soup(html)
        return self.extract_images(soup.body or soup,chapter.url,prefix=f"chapter-{chapter.number}"),True

    def refresh_tail(self,story):
        refreshed=self.fetch_story(story.source_url)
        known={c.external_id for c in story.chapters}
        return [c for c in refreshed.chapters if c.external_id not in known]
