from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse


class BasePlatformAdapter(ABC):
    name = "base"
    family = "base"

    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    @staticmethod
    def host(url: str) -> str:
        return urlparse(url).netloc.lower().split(":", 1)[0]

    @staticmethod
    def absolute_url(base_url: str, href: str) -> str:
        return urljoin(base_url, href)
