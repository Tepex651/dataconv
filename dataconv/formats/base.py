"""Base handler — auto-registers subclasses by their ``formats`` class attribute."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TextIO

from dataconv.support import InputFileError, OutputFileError


_REGISTRY: dict[str, type["BaseHandler"]] = {}


def get_handler(format_name: str) -> type["BaseHandler"]:
    """Look up a format handler by extension or format name."""
    key = format_name if format_name.startswith(".") else f".{format_name}"
    handler = _REGISTRY.get(key) or _REGISTRY.get(format_name)
    if handler is None:
        from dataconv.support import UnsupportedFormatError

        raise UnsupportedFormatError(
            f"Available: {sorted(_REGISTRY.keys())}"
        )
    return handler


def registered_formats() -> list[str]:
    """Return all registered format extensions (for CLI help, tests, etc.)."""
    return sorted(_REGISTRY.keys())


class BaseHandler(ABC):
    """Subclass this and set ``formats`` to auto-register.

    Example:
        class XMLFormat(BaseHandler):
            formats = {"xml"}

            def read(self, path: Path) -> list[dict]: ...
            def write(self, path: Path, data: list[dict]) -> None: ...
    """

    formats: set[str] = set()

    def __init_subclass__(cls, **kwargs: dict) -> None:
        super().__init_subclass__(**kwargs)
        for fmt in cls.formats:
            key = fmt if fmt.startswith(".") else f".{fmt}"
            _REGISTRY[key] = cls

    @abstractmethod
    def read(self, path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def write(self, path: Path, data: list[dict]) -> None:
        raise NotImplementedError

    def _open_for_read(self, path: Path) -> TextIO:
        try:
            return path.open("r", encoding="utf-8")
        except Exception as e:
            raise InputFileError(str(path)) from e

    def _open_for_write(self, path: Path) -> TextIO:
        try:
            return path.open("w", encoding="utf-8")
        except Exception as e:
            raise OutputFileError(str(path)) from e
