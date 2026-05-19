"""Support — validation and exceptions."""

from __future__ import annotations

import importlib.util
import logging
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

from pydantic import BaseModel

log = logging.getLogger("dataconv")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConverterError(Exception):
    pass


class InputFileError(ConverterError):
    pass


class OutputFileError(ConverterError):
    pass


class UnsupportedFormatError(ConverterError):
    pass


# ---------------------------------------------------------------------------
# Flatten / Unflatten utilities
# ---------------------------------------------------------------------------


def _flatten(data: Any, parent_key: str = "", sep: str = ".") -> dict:
    """Recursively flatten a nested dict into a flat dict with dotted keys."""
    items: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(_flatten(v, new_key, sep).items())
            elif isinstance(v, list):
                # lists at leaf level are kept as-is
                items.append((new_key, v))
            else:
                items.append((new_key, v))
    return dict(items)


def _unflatten(data: dict, sep: str = ".") -> dict:
    """Unflatten a flat dict with dotted keys into a nested dict."""
    result: dict = {}
    for key, value in data.items():
        parts = key.split(sep)
        current = result
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def _is_nested(data: dict) -> bool:
    """Check if any value in the dict is itself a dict (non-None)."""
    return any(isinstance(v, dict) for v in data.values())


def _is_schema_nested(model: type) -> bool:
    """Check if the Pydantic model has any nested BaseModel fields."""
    for field_info in model.model_fields.values():
        ann = field_info.annotation
        # Handle Union types: typing.Union[X, None] and types.UnionType (X | None)
        if hasattr(ann, "__origin__"):
            origin = ann.__origin__
            if origin is Union or origin is types.UnionType:
                args = ann.__args__
                for arg in args:
                    if arg is type(None):
                        continue
                    if isinstance(arg, type) and issubclass(arg, BaseModel):
                        return True
        elif isinstance(ann, type) and issubclass(ann, BaseModel):
            return True
    return False


def _flatten_list(data: list[dict]) -> list[dict]:
    """Flatten each row in a list of dicts."""
    return [_flatten(row) for row in data]


def _unflatten_list(data: list[dict]) -> list[dict]:
    """Unflatten each row in a list of dicts."""
    return [_unflatten(row) for row in data]


def _has_dotted_keys(data: list[dict]) -> bool:
    """Check if any row has dotted keys."""
    return any("." in k for row in data for k in row)


def _truncate_keys(data: list[dict]) -> list[dict]:
    """Strip dotted prefixes from keys, keeping only the last segment.

    Warns if multiple dotted keys collapse to the same short name.
    """
    all_keys = [k for row in data for k in row]
    short_keys = [k.split(".")[-1] for k in all_keys]
    seen = set()
    collisions = set()
    for sk in short_keys:
        if sk in seen and sk not in collisions:
            collisions.add(sk)
        seen.add(sk)

    if collisions:
        log.warning(
            "Key collision in --csv-keys flat mode: %s — "
            "only the last value will be kept. Consider using --csv-keys dotted",
            sorted(collisions),
        )

    result = []
    for row in data:
        result.append({k.split(".")[-1]: v for k, v in row.items()})
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    valid: bool
    data: dict
    errors: list[str]


class Validator:
    def __init__(self, schema_path: str | None = None):
        self._model = None
        if schema_path:
            self._load_schema(Path(schema_path))

    @property
    def has_schema(self) -> bool:
        return self._model is not None

    def _load_schema(self, path: Path) -> None:
        if not path.exists():
            log.warning("Schema file not found: %s — skipping validation", path)
            return

        try:
            spec = importlib.util.spec_from_file_location("schema", path)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[arg-type]

            from pydantic import BaseModel

            for val in vars(mod).values():
                if isinstance(val, type) and issubclass(val, BaseModel) and val is not BaseModel:
                    self._model = val
                    log.info("Loaded schema: %s", self._model.__name__)
                    return

            # Module loaded but no BaseModel found
            log.warning("No Pydantic BaseModel found in %s — skipping validation", path)
        except Exception as exc:
            log.error("Failed to load schema from %s: %s — skipping validation", path, exc)

    def validate(self, data: dict) -> ValidationResult:
        if self._model is None:
            return ValidationResult(valid=True, data=data, errors=[])

        input_is_nested = _is_nested(data)
        schema_is_nested = _is_schema_nested(self._model)

        # Transform input to match schema shape
        if input_is_nested and not schema_is_nested:
            data = _flatten(data)
        elif not input_is_nested and schema_is_nested:
            data = _unflatten(data)

        try:
            validated = self._model.model_validate(data).model_dump()
            result = validated
            # Transform result back to input shape
            if input_is_nested and not schema_is_nested:
                # Input was nested, output from flat schema is flat -> unflatten
                result = _unflatten(result)
            elif not input_is_nested and schema_is_nested:
                # Input was flat, output from nested schema is nested -> flatten
                result = _flatten(result)
            return ValidationResult(valid=True, data=result, errors=[])
        except Exception as e:
            return ValidationResult(valid=False, data=data, errors=str(e).split("\n"))
