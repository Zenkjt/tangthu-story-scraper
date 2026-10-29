from __future__ import annotations
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

TARGET = "https://kenhtruyenfull.com/truyen/tru-tien"
OUT_DIR = Path(".debug-kenhtruyenfull")
KEYWORDS = ("chuong", "chapter", "list", "ajax", "api", "page",
            "pagination", "loadmore", "load-more")

class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.scripts = []
        self.forms = []
        self._src = None
        self._chunks = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.links.append((d["href"], d.get("title", "")))
        elif tag == "script":
            self._in_script = True
            self._src = d.get("src")
            self._chunks = []
        elif tag == "form":
            self.forms.append((d.get("action", ""), d.get("method", ""),
                               d.get("class", "")))

    def handle_data(self, data):
        if self._in_script:
            self._chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self.scripts.append((self._src, "".join(self._chunks)))
            self._in_script = False
            self._src = None
            self._chunks = []

def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "Chrome/131.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
    })
    with urlopen(req, timeout=45) as r:
        body = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
        return body.decode(charset, errors="replace"), r.geturl(), r.status

def interesting(v):
    return any(k in v.casefold() for k in KEYWORDS)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html, final_url, status = fetch(TARGET)
    (OUT_DIR / "story.html").write_text(html, encoding="utf-8")

    p = Collector()
    p.feed(html)
    lines = [
        "=== KenhTruyenFull debug ===",
        f"TARGET: {TARGET}",
        f"FINAL_URL: {final_url}",
        f"STATUS: {status}",
        f"HTML_BYTES: {len(html.encode('utf-8'))}",
        f"LINK_COUNT: {len(p.links)}",
        f"SCRIPT_COUNT: {len(p.scripts)}",
        f"FORM_COUNT: {len(p.forms)}",
        "",
    ]

    chapters = []
    seen = set()
    for href, title in p.links:
        u = urljoin(final_url, href)
        if re.search(r"/doc-truyen/[^/?#]+/chuong-\d+/?$", urlparse(u).path, re.I):
            key = u.rstrip("/").casefold()
            if key not in seen:
                seen.add(key)
                chapters.append(u)

    lines.append(f"DIRECT_CHAPTER_LINKS: {len(chapters)}")
    lines.extend(f"  CHAPTER: {u}" for u in chapters[:200])
    lines.append("")
    lines.append("KEYWORD LINKS:")
    hits = [(h, t) for h, t in p.links if interesting(h) or interesting(t)]
    lines.extend(f"  href={h!r} title={t!r}" for h, t in hits[:500])
    if not hits:
        lines.append("  (none)")
    lines.append("")
    lines.append("SCRIPT SOURCES:")
    for src, _ in p.scripts:
        if src:
            lines.append(f"  {urljoin(final_url, src)}")
    lines.append("")
    lines.append("INTERESTING INLINE SCRIPT SNIPPETS:")
    count = 0
    for i, (src, body) in enumerate(p.scripts, 1):
        if not body or not interesting(body):
            continue
        compact = re.sub(r"\s+", " ", body).strip()
        for kw in KEYWORDS:
            pos = compact.casefold().find(kw.casefold())
            if pos >= 0:
                lines.append(
                    f"  script[{i}] src={src!r} keyword={kw!r}: "
                    f"{compact[max(0,pos-250):min(len(compact),pos+750)]}"
                )
                count += 1
                if count >= 30:
                    break
        if count >= 30:
            break
    if not count:
        lines.append("  (none)")
    lines.append("")
    lines.append("FORMS:")
    for a, m, c in p.forms:
        lines.append(f"  action={a!r} method={m!r} class={c!r}")
    if not p.forms:
        lines.append("  (none)")
    lines.append("")
    lines.append("SAMPLE LINKS (first 150):")
    lines.extend(f"  href={h!r} title={t!r}" for h, t in p.links[:150])

    report = "\n".join(lines) + "\n"
    (OUT_DIR / "report.txt").write_text(report, encoding="utf-8")
    print(report)
    print("Saved raw HTML: .debug-kenhtruyenfull/story.html")
    print("Saved report:   .debug-kenhtruyenfull/report.txt")

if __name__ == "__main__":
    main()
