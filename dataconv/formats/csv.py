"""CSV format handler — flattens nested data for write, reads flat rows."""

import csv
from typing import TextIO

from dataconv.config import CsvKeys
from dataconv.utils import _flatten_list, _has_dotted_keys, _truncate_keys, _unflatten_list

from .base import BaseHandler


class CSVFormat(BaseHandler):
    formats = {"csv"}

    def _transform_for_read(self, data: list[dict]) -> list[dict]:
        """Unflatten dotted keys back into nested structures."""
        return _unflatten_list(data)

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Flatten nested data and optionally truncate dotted keys."""
        flat = _flatten_list(data)
        if self.config and self.config.csv_keys == CsvKeys.flat:
            if _has_dotted_keys(flat):
                flat = _truncate_keys(flat)
        return flat

    def _read_from(self, f: TextIO) -> list[dict]:
        return list(csv.DictReader(f))

    def _get_fieldnames(self, data: list[dict]) -> list[str]:
        """Collect fieldnames preserving insertion order."""
        seen: dict[str, None] = {}
        for row in data:
            for key in row:
                seen.setdefault(key, None)
        return list(seen)

    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        fieldnames = self._get_fieldnames(data)
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
