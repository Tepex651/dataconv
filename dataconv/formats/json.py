"""JSON format handler."""

import json
from pathlib import Path

from .base import BaseHandler


class JSONFormat(BaseHandler):
    formats = {"json"}

    def read(self, path: Path) -> list[dict]:
        with self._open_for_read(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        raise ValueError(
            f"JSON root must be object or array, got {type(data).__name__}"
         )

    def write(self, path: Path, data: list[dict]) -> None:
        with self._open_for_write(path) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
