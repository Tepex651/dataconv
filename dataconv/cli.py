"""Minimal CLI — convert between data formats."""

import argparse
import logging
import sys

from dataconv.config import Config, CsvKeys
from dataconv.converter import Converter
from dataconv.formats import registered_formats

log = logging.getLogger("dataconv")


def _is_format(arg: str) -> bool:
    """Return True if *arg* is a registered format name (no dot, matches registry)."""
    return "." not in arg and arg in registered_formats()


def _resolve(
    inp: str,
    out: str,
) -> tuple[str, str]:
    """Turn positional args into (input_path_or_fmt, output_path_or_fmt).

    Rules:
      - Contains ``.`` → file path (format auto-detected from extension).
      - No ``.`` and a valid format name → format name (stream: stdin/stdout).
    """
    return inp, out


def main() -> int:
    fmts = ", ".join(registered_formats())
    parser = argparse.ArgumentParser(
        prog="dataconv",
        description="Convert files between formats.",
        epilog=(
            f"Formats: {fmts}\n\n"
            "Examples:\n"
            "  dataconv input.json output.csv\n"
            "  dataconv input.csv output.json --schema schema.py\n"
            "  dataconv input.json output.csv --csv-keys flat\n"
            "  dataconv input.json output.json --flatten\n"
            "  cat input.json | dataconv json csv\n"
            "  dataconv input.json csv | less\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input file path or format name for stdin",
    )
    parser.add_argument(
        "output",
        help="Output file path or format name for stdout",
    )
    parser.add_argument("--schema", default=None, help="Path to Pydantic schema file")
    parser.add_argument("-e", "--errors", default=None, help="Path for invalid rows")
    parser.add_argument(
        "--flatten",
        action="store_true",
        default=False,
        help="Flatten nested objects in output (default: keep nested)",
    )
    parser.add_argument(
        "--csv-keys",
        choices=["dotted", "flat"],
        default="dotted",
        help="CSV column naming: dotted=address.city (default), flat=city",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(name)s: %(message)s")

    input_path, output_path = _resolve(args.input, args.output)

    try:
        config = Config(
            flatten=args.flatten,
            csv_keys=CsvKeys(args.csv_keys),
        )
        Converter(
            input_path=input_path,
            output_path=output_path,
            config=config,
            error_path=args.errors,
            schema_path=args.schema,
        ).run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
