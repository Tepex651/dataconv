"""Converter - read -> validate -> write."""

import sys
from pathlib import Path

from dataconv.config import Config
from dataconv.formats import get_handler, registered_formats
from dataconv.formats.base import BaseHandler
from dataconv.utils import Validator


def _is_format_name(name: str) -> bool:
    """Return True if *name* is a format name (no dot, in registry)."""
    name = str(name)
    if "." in name:
        return False
    return f".{name}" in registered_formats()


def _resolve_format(path: str) -> str | None:
    """Try to detect format from file extension."""
    suffix = Path(path).suffix.lstrip(".")
    if suffix and f".{suffix}" in registered_formats():
        return suffix
    return None


class Converter:
    def __init__(
        self,
        input_path: str,
        output_path: str,
        config: Config | None = None,
        error_path: str | None = None,
        schema_path: str | None = None,
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.error_path = error_path
        self.validator = Validator(schema_path)
        self.config = config or Config()

    def _get_handler(self, path: str) -> "BaseHandler":
        """Get handler for a path or format name."""
        if _is_format_name(path):
            fmt = str(path)
        else:
            fmt = _resolve_format(str(path))
        if fmt is None:
            raise ValueError(
                f"Cannot detect format for {path!r} - use a known file extension"
            )
        return get_handler(f".{fmt}", self.config)

    def _read(self) -> list[dict]:
        handler = self._get_handler(self.input_path)
        if _is_format_name(self.input_path):
            return handler.read_stdin(sys.stdin)
        return handler.read(Path(self.input_path))

    def _write(self, data: list[dict]) -> None:
        handler = self._get_handler(self.output_path)
        if _is_format_name(self.output_path):
            handler.write_stdout(sys.stdout, data)
        else:
            handler.write(Path(self.output_path), data)

    def run(self) -> None:
        # Read
        data = self._read()

        # Validate
        valid_data: list[dict] = []
        invalid_rows: list[dict] = []
        if self.validator.has_schema:
            for row in data:
                result = self.validator.validate(row)
                if result.valid:
                    valid_data.append(result.data)
                else:
                    invalid_rows.append({"data": row, "errors": result.errors})
        else:
            valid_data = data

        # Write
        self._write(valid_data)

        # Write errors
        if invalid_rows and self.error_path:
            err_handler = self._get_handler(self.error_path)
            err_handler.write(Path(self.error_path), invalid_rows)
