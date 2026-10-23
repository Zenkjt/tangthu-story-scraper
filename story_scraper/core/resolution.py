from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


@dataclass(frozen=True)
class AdapterResolutionRecord:
    domain: str
    adapter: str
    result: str
    reason: str
    timestamp: str
    url: str | None = None


@dataclass(frozen=True)
class AdapterCoverage:
    domain: str
    status: str  # "good" | "failure" | "unknown"
    adapter: str | None = None
    reason: str | None = None
    timestamp: str | None = None
    url: str | None = None


class AdapterResolutionStore:
    """Global adapter-resolution history plus a derived active coverage index."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self, domain: str, adapter: str, result: str, reason: str,
        url: str | None = None,
    ) -> AdapterResolutionRecord:
        item = AdapterResolutionRecord(
            domain=domain, adapter=adapter, result=result, reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(), url=url,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return item

    def records(self) -> list[AdapterResolutionRecord]:
        if not self.path.exists():
            return []
        return [
            AdapterResolutionRecord(**json.loads(line))
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def latest_for_domain(self, domain: str) -> AdapterResolutionRecord | None:
        for item in reversed(self.records()):
            if item.domain == domain:
                return item
        return None

    def coverage(self, domain: str) -> AdapterCoverage:
        item = self.latest_for_domain(domain)
        if item is None:
            return AdapterCoverage(domain, "unknown")
        return AdapterCoverage(
            domain,
            "good" if item.result == "success" else "failure",
            item.adapter,
            item.reason,
            item.timestamp,
            item.url,
        )

    def active_coverage(self) -> list[AdapterCoverage]:
        domains = {item.domain for item in self.records()}
        return [self.coverage(domain) for domain in sorted(domains)]

    def coverage_for_adapter(self, adapter: str, status: str | None = None) -> list[AdapterCoverage]:
        items = [
            item for item in self.active_coverage()
            if item.adapter == adapter and (status is None or item.status == status)
        ]
        return items

    def known_good(self, domain: str) -> bool:
        return self.coverage(domain).status == "good"

    def known_failure(self, domain: str) -> bool:
        return self.coverage(domain).status == "failure"

    def latest_success(self, domain: str) -> str | None:
        item = self.latest_for_domain(domain)
        if item is not None and item.result == "success":
            return item.adapter
        return None

    def known_good_list(self) -> list[AdapterCoverage]:
        return [item for item in self.active_coverage() if item.status == "good"]

    def failure_list(self) -> list[AdapterCoverage]:
        return [item for item in self.active_coverage() if item.status == "failure"]

    def recheck_required(self, domain: str) -> bool:
        return self.coverage(domain).status == "failure"


def resolution_domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def classify_resolution_failure(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 403:
            return "HTTP_403"
        if exc.code == 404:
            return "HTTP_404"
        if 500 <= exc.code <= 599:
            return "HTTP_5XX"
        return f"HTTP_{exc.code}"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "TIMEOUT"
    if isinstance(exc, URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "TIMEOUT"
        if isinstance(reason, socket.gaierror):
            return "DNS_ERROR"
        return "UNKNOWN_ERROR"
    message = str(exc).lower()
    if "parse" in message:
        return "PARSE_ERROR"
    if "metadata" in message:
        return "NO_STORY_METADATA"
    if "chapter" in message and "link" in message:
        return "NO_CHAPTER_LINKS"
    if "blocked" in message or "challenge" in message or "captcha" in message:
        return "BLOCKED_OR_CHALLENGE"
    if "invalid" in message and "url" in message:
        return "INVALID_CHAPTER_URL"
    return "UNKNOWN_ERROR"
