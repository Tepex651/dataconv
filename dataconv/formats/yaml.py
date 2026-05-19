"""YAML format handler."""

from typing import TextIO

from dataconv.utils import _flatten_list

from .base import BaseHandler

try:
    import yaml
except ImportError:
    yaml = None   # type: ignore[assignment]


class YAMLFormat(BaseHandler):
    formats = {"yaml", "yml"}

    def __init__(self, config=None) -> None:
        super().__init__(config=config)
        if yaml is None:
            raise ImportError(
                  "PyYAML is required for YAML support. Install with: pip install pyyaml"
              )

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Flatten nested data if --flatten is enabled."""
        if self.config is not None and self.config.flatten:
            return _flatten_list(data)
        return data

    def _read_from(self, f: TextIO) -> list[dict]:
        docs = list(yaml.safe_load_all(f))
          # Filter out None docs (blank separators produce None)
        docs = [d for d in docs if d is not None]

        if not docs:
            return []

          # Single dict -> wrap in list
        if len(docs) == 1 and isinstance(docs[0], dict):
            return [docs[0]]

          # List of dicts or single list
        result = []
        for doc in docs:
            if isinstance(doc, list):
                result.extend(doc)
            elif isinstance(doc, dict):
                result.append(doc)
        return result

    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        yaml.dump_all(data, f, default_flow_style=False, allow_unicode=True)
