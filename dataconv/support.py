"""Support — validation and exceptions."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


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
            return

        try:
            spec = importlib.util.spec_from_file_location("schema", path)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[arg-type]

            from pydantic import BaseModel

            for val in vars(mod).values():
                if isinstance(val, type) and issubclass(val, BaseModel) and val is not BaseModel:
                    self._model = val
                    break
        except Exception:
            pass

    def validate(self, data: dict) -> ValidationResult:
        if self._model is None:
            return ValidationResult(valid=True, data=data, errors=[])

        try:
            validated = self._model.model_validate(data).model_dump()
            return ValidationResult(valid=True, data=validated, errors=[])
        except Exception as e:
            return ValidationResult(valid=False, data=data, errors=str(e).split("\n"))
