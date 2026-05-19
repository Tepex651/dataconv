"""JSON format handler."""

import json
from typing import TextIO

from dataconv.utils import _flatten_list

from .base import BaseHandler


class JSONFormat(BaseHandler):
    formats = {"json"}

    def _read_from(self, f: TextIO) -> list[dict]:
        data = json.load(f)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        raise ValueError(
            f"JSON root must be object or array, got {type(data).__name__}"
          )

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Flatten nested data and optionally truncate dotted keys."""
        if self.config and self.config.flatten:
            data = _flatten_list(data)
        return data

    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
