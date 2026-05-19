"""NDJSON / JSONLines format handler — one JSON object per line."""

import json
import logging
from typing import TextIO

from dataconv.utils import _flatten_list

from .base import BaseHandler

log = logging.getLogger("dataconv")


class NDJSONFormat(BaseHandler):
    formats = {"ndjson", "jsonl"}

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Flatten nested data if --flatten is enabled."""
        if self.config is not None and self.config.flatten:
            return _flatten_list(data)
        return data

    def _read_from(self, f: TextIO) -> list[dict]:
        rows = []
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                log.warning("Skipping malformed JSON at line %d: %s", lineno, exc)
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            elif isinstance(obj, list):
                  # A single line containing an array — flatten into rows
                rows.extend(obj)
            else:
                log.warning("Skipping non-object at line %d", lineno)
        return rows

    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        for row in data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
