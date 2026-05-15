"""Minimal CLI — convert between data formats."""

import argparse
import sys

from dataconv.converter import Converter


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dataconv",
        description="Convert files between formats (json, csv).",
        epilog="Examples:\n"
               "  dataconv input.json output.csv\n"
               "  dataconv input.csv output.json --schema schema.py\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--schema", default=None, help="Path to Pydantic schema file")
    parser.add_argument("-e", "--errors", default=None, help="Path for invalid rows")

    args = parser.parse_args()

    try:
        Converter(args.input, args.output, args.errors, args.schema).run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
