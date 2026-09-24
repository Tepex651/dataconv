"""XML format handler — ``<rows><row>…</row></rows>`` of nested records."""

import re
import xml.etree.ElementTree as ET
from typing import TextIO

from dataconv.utils import InputFileError, _flatten_list

from .base import BaseHandler

_TAG_RE = re.compile(r"[^0-9A-Za-z_.\-]")


def _local_name(tag: str) -> str:
    """Strip an XML namespace, keeping the local part of a tag name."""
    return tag.split("}")[-1]


def _sanitize_tag(key: str) -> str:
    """Coerce an arbitrary key into a valid XML element name."""
    tag = _TAG_RE.sub("_", str(key))
    if not tag or not (tag[0].isalpha() or tag[0] in "_:"):
        tag = "_" + tag
    return tag


def _text(elem: "ET.Element") -> str | None:
    """Return stripped text of a leaf element, or ``None`` when empty."""
    value = (elem.text or "").strip()
    return value or None


def _element_to_dict(elem: "ET.Element") -> dict:
    """Convert an XML element into a dict.

    Child elements become fields (namespaces stripped); a repeated tag
    collapses into a list; nested children recurse; attributes are merged
    under an ``@`` prefix.
    """
    result: dict = {}
    for name, value in elem.attrib.items():
        result["@" + _local_name(name)] = value

    for child in elem:
        key = _local_name(child.tag)
        value = _element_to_dict(child) if len(child) else _text(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _scalar(value: object) -> str | None:
    """Stringify a scalar for ``.text``; ``None`` yields an empty element."""
    return None if value is None else str(value)


def _dict_to_element(parent: "ET.Element", data: dict) -> None:
    """Append child elements to ``parent`` from a dict.

    Nested dicts recurse; lists repeat the same tag; scalars become text.
    """
    for key, value in data.items():
        tag = _sanitize_tag(key)
        if isinstance(value, dict):
            child = ET.SubElement(parent, tag)
            _dict_to_element(child, value)
        elif isinstance(value, list):
            for item in value:
                child = ET.SubElement(parent, tag)
                if isinstance(item, dict):
                    _dict_to_element(child, item)
                else:
                    child.text = _scalar(item)
        else:
            child = ET.SubElement(parent, tag)
            child.text = _scalar(value)


class XMLFormat(BaseHandler):
    formats = {"xml"}

    def _transform_for_write(self, data: list[dict]) -> list[dict]:
        """Flatten nested data if --flatten is enabled."""
        if self.config is not None and self.config.flatten:
            return _flatten_list(data)
        return data

    def _read_from(self, f: TextIO) -> list[dict]:
        text = f.read()
        if not text.strip():
            return []
        try:
            root = ET.XML(text)
        except ET.ParseError as exc:
            raise InputFileError(str(exc)) from exc
        children = list(root)
        if children and all(_local_name(c.tag) == _local_name(children[0].tag) for c in children):
            return [_element_to_dict(c) for c in children]
        return [_element_to_dict(root)]

    def _write_to(self, f: TextIO, data: list[dict]) -> None:
        root_tag = "rows"
        item_tag = "row"
        if self.config is not None:
            root_tag = self.config.xml_root
            item_tag = self.config.xml_item
        root = ET.Element(_sanitize_tag(root_tag))
        item = _sanitize_tag(item_tag)
        for row in data:
            row_elem = ET.SubElement(root, item)
            _dict_to_element(row_elem, row)
        ET.indent(root)
        f.write(ET.tostring(root, encoding="unicode"))
