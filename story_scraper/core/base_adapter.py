from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse


class BasePlatformAdapter(ABC):
    name = "base"
    family = "base"

    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    @classmethod
    def probe(cls, url: str) -> bool:
        return cls.matches(url)

    @staticmethod
    def host(url: str) -> str:
        return urlparse(url).netloc.lower().split(":", 1)[0].removeprefix("www.")

    @staticmethod
    def absolute_url(base_url: str, href: str) -> str:
        from urllib.parse import urljoin
        return urljoin(base_url, href)

    def fetch_initial_target_on_register(self, story) -> bool:
        """Whether registration should immediately fetch the selected target."""
        return False
