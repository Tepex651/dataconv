"""Converter — read → validate → write."""

from pathlib import Path

from dataconv.formats import get_handler
from dataconv.support import Validator


class Converter:
    def __init__(
        self,
        input_path: str,
        output_path: str,
        error_path: str | None = None,
        schema_path: str | None = None,
    ):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.error_path = Path(error_path) if error_path else None
        self.validator = Validator(schema_path)

    def _get_format(self, path: Path) -> str:
        fmt = path.suffix.lstrip(".")
        if not fmt:
            raise ValueError(f"Cannot detect format for {path}")
        return fmt

    def run(self) -> None:
        # Read
        in_handler = get_handler(self._get_format(self.input_path))()
        data = in_handler.read(self.input_path)

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
        out_handler = get_handler(self._get_format(self.output_path))()
        out_handler.write(self.output_path, valid_data)

        # Write errors
        if invalid_rows and self.error_path:
            err_handler = get_handler(self._get_format(self.error_path))()
            err_handler.write(self.error_path, invalid_rows)
