"""CSV format handler — flattens nested data for write, reads flat rows."""

import csv
from pathlib import Path
from typing import Any

from .base import BaseHandler


def _flatten_data(
    data: Any,
    parent_key: str = "",
    sep: str = ".",
) -> list[dict]:
    """Recursively flatten nested dict/list structures into flat dicts."""
    if isinstance(data, dict):
        result = [{}]
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            flattened = _flatten_data(v, new_key, sep)
            result = _merge_contexts(result, flattened)
        return result

    if isinstance(data, list):
        combined: list[dict] = []
        for el in data:
            combined.extend(_flatten_data(el, parent_key, sep))
        return combined

    return [{parent_key: data}]


def _merge_contexts(
    contexts: list[dict],
    new_items: list[dict],
) -> list[dict]:
    """Cartesian product of parent contexts with child items."""
    return [{**base, **new} for base in contexts for new in new_items]


class CSVFormat(BaseHandler):
    formats = {"csv"}

    def read(self, path: Path) -> list[dict]:
        with self._open_for_read(path) as f:
            return list(csv.DictReader(f))

    def write(self, path: Path, data: list[dict]) -> None:
        flat = _flatten_data(data)
        fieldnames = sorted({key for row in flat for key in row})
        with self._open_for_write(path) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat)
