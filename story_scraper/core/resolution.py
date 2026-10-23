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


class KnownResolutionFailure(RuntimeError):
    """Raised when a domain is already known to be unsupported."""


class AdapterResolutionStore:
    """Global, append-only adapter resolution history."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        domain: str,
        adapter: str,
        result: str,
        reason: str,
    ) -> AdapterResolutionRecord:
        item = AdapterResolutionRecord(
            domain=domain,
            adapter=adapter,
            result=result,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return item

    def records(self) -> list[AdapterResolutionRecord]:
        if not self.path.exists():
            return []
        result: list[AdapterResolutionRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                result.append(AdapterResolutionRecord(**json.loads(line)))
        return result

    def latest(self, domain: str) -> AdapterResolutionRecord | None:
        for item in reversed(self.records()):
            if item.domain == domain:
                return item
        return None

    def latest_success(self, domain: str) -> str | None:
        item = self.latest(domain)
        if item is not None and item.result == "success":
            return item.adapter
        return None

    def latest_failure(self, domain: str) -> AdapterResolutionRecord | None:
        item = self.latest(domain)
        if item is not None and item.result == "failure":
            return item
        return None

    def failed_adapters_since_latest_success(self, domain: str) -> set[str]:
        items = [item for item in self.records() if item.domain == domain]
        failed: set[str] = set()
        for item in reversed(items):
            if item.result == "success":
                break
            if item.result == "failure":
                failed.add(item.adapter)
        return failed

    def known_good(self) -> dict[str, AdapterResolutionRecord]:
        latest_by_domain: dict[str, AdapterResolutionRecord] = {}
        for item in self.records():
            latest_by_domain[item.domain] = item
        return {
            domain: item
            for domain, item in latest_by_domain.items()
            if item.result == "success"
        }

    def known_failures(self) -> dict[str, AdapterResolutionRecord]:
        latest_by_domain: dict[str, AdapterResolutionRecord] = {}
        for item in self.records():
            latest_by_domain[item.domain] = item
        return {
            domain: item
            for domain, item in latest_by_domain.items()
            if item.result == "failure"
        }

    def coverage(self) -> dict[str, dict[str, str]]:
        latest_by_domain: dict[str, AdapterResolutionRecord] = {}
        for item in self.records():
            latest_by_domain[item.domain] = item

        return {
            domain: {
                "status": "known_good" if item.result == "success" else "known_failure",
                "adapter": item.adapter,
                "reason": item.reason,
                "timestamp": item.timestamp,
            }
            for domain, item in latest_by_domain.items()
        }


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
