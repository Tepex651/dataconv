"""Base handler — auto-registers subclasses by their ``formats`` class attribute."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from dataconv.utils import InputFileError, OutputFileError

if TYPE_CHECKING:
    from dataconv.config import Config


_REGISTRY: dict[str, type[BaseHandler]] = {}


def get_handler(format_name: str, config: Config | None = None) -> BaseHandler:
    """Look up a format handler by name and instantiate it."""
    handler_cls = _REGISTRY.get(format_name)
    if handler_cls is None:
        from dataconv.utils import UnsupportedFormatError

        raise UnsupportedFormatError(f"Available: {sorted(_REGISTRY.keys())}")
    return handler_cls(config=config)


def registered_formats() -> list[str]:
    """Return all registered format extensions (for CLI help, tests, etc.)."""
    return sorted(_REGISTRY.keys())


class BaseHandler(ABC):
    """Subclass this and set ``formats`` to auto-register.

    Subclasses implement ``_read_from(f)`` and ``_write_to(f, data)`` which work
    with any ``TextIO`` stream. The base class provides ``read``, ``write``,
    ``read_stdin``, and ``write_stdout`` that handle file opening / stream routing.
    """

    formats: set[str] = set()

    def __init__(self, config: Config | None = None) -> None:
        self.config = config

    def __init_subclass__(cls, **kwargs: dict) -> None:
        super().__init_subclass__(**kwargs)
        for fmt in cls.formats:
            key = fmt if fmt.startswith(".") else f".{fmt}"
            _REGISTRY[key] = cls

    # -- abstract methods subclasses MUST implement -----------------------

    @abstractmethod
    def _read_from(self, f: TextIO) -> list[dict]:
        """Read data from a text stream and return a list of dicts."""
        raise NotImplementedError

    @abstractmethod
    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        """Write data to a text stream."""
        raise NotImplementedError

    # -- optional transforms ---------------------------------------------

    def _transform_for_read(self, data: list[dict]) -> list[dict]:
        """Transform data after reading, before validation.

        Override in subclasses to normalize data shape
        (e.g., unflatten CSV rows with dotted keys).
        """
        return data

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Transform data before writing.

        Override in subclasses to adapt data to the target format
        (e.g., flatten nested dicts for CSV output).
        """
        return data

    # -- unified read/write entry points ---------------------------------

    def read(self, path: Path) -> list[dict]:
        with self._open_for_read(path) as f:
            data = self._read_from(f)
        return self._transform_for_read(data)

    def write(self, path: Path, data: list[dict]) -> None:
        data = self._transform_for_write(data)
        with self._open_for_write(path) as f:
            self._write_to(f, data)

    def read_stdin(self, stdin: TextIO) -> list[dict]:
        data = self._read_from(stdin)
        return self._transform_for_read(data)

    def write_stdout(self, stdout: TextIO, data: list[dict]) -> None:
        data = self._transform_for_write(data)
        self._write_to(stdout, data)

    # -- helpers ---------------------------------------------------------

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
