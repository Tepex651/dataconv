"""Tests for CLI — argument wiring and end-to-end behavior."""

import json
import logging
import sys
from unittest import mock

import pytest

from dataconv.cli import main


class TestArgumentWiring:
    """Verify that CLI arguments are correctly passed to Converter."""

    def test_file_to_file(self, tmp_path):
        inp = tmp_path / "input.json"
        out = tmp_path / "output.csv"
        inp.write_text(json.dumps([{"name": "Alice"}]))

        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", str(inp), str(out)]
            main()

        mock_conv.assert_called_once()
        call_kwargs = mock_conv.call_args[1]
        assert call_kwargs["input_path"] == str(inp)
        assert call_kwargs["output_path"] == str(out)

    def test_format_to_format(self):
        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", "json", "csv"]
            main()

        call_kwargs = mock_conv.call_args[1]
        assert call_kwargs["input_path"] == "json"
        assert call_kwargs["output_path"] == "csv"

    def test_schema_flag_is_passed(self, tmp_path):
        schema = tmp_path / "schema.py"
        schema.write_text("")

        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", "json", "csv", "--schema", str(schema)]
            main()

        call_kwargs = mock_conv.call_args[1]
        assert call_kwargs["schema_path"] == str(schema)

    def test_errors_flag_is_passed(self, tmp_path):
        errors = tmp_path / "errors.json"

        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", "json", "csv", "-e", str(errors)]
            main()

        call_kwargs = mock_conv.call_args[1]
        assert call_kwargs["error_path"] == str(errors)

    def test_flatten_flag_is_passed(self):
        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", "json", "csv", "--flatten"]
            main()

        call_kwargs = mock_conv.call_args[1]
        config = call_kwargs["config"]
        assert config.flatten is True

    def test_csv_keys_flag_is_passed(self):
        with mock.patch("dataconv.cli.Converter") as mock_conv:
            sys.argv = ["dataconv", "json", "csv", "--csv-keys", "flat"]
            main()

        call_kwargs = mock_conv.call_args[1]
        config = call_kwargs["config"]
        assert config.csv_keys.value == "flat"


class TestEndToEnd:
    """Real conversions through the CLI (no mocking)."""

    def run_cli(self, args, stdin_text=None):
        """Helper: run main() with given args and optional stdin, return (exit_code, stdout, stderr)."""
        stdout_buf = mock.MagicMock()
        stderr_buf = mock.MagicMock()
        old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr

        try:
            if stdin_text is not None:
                sys.stdin = mock.MagicMock(read=mock.MagicMock(return_value=stdin_text))
            sys.stdout = stdout_buf
            sys.stderr = stderr_buf
            sys.argv = ["dataconv"] + args

            try:
                result = main()
            except SystemExit as e:
                result = e.code

            stdout = stdout_buf.write.call_args_list
            stderr = stderr_buf.write.call_args_list
            return (
                result,
                "".join(ca[0][0] for ca in stdout),
                "".join(ca[0][0] for ca in stderr),
            )
        finally:
            sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr

    def test_file_to_file_conversion(self, tmp_path):
        inp = tmp_path / "input.json"
        out = tmp_path / "output.csv"
        inp.write_text(json.dumps([{"id": 1, "name": "Alice"}]))

        code, stdout, stderr = self.run_cli([str(inp), str(out)])
        assert code == 0
        text = out.read_text()
        assert "id,name" in text
        assert "Alice" in text

    def test_stdin_to_stdout(self):
        code, stdout, stderr = self.run_cli(
            ["json", "csv"],
            stdin_text=json.dumps([{"id": 1, "name": "Bob"}]),
        )
        assert code == 0
        assert "id,name" in stdout
        assert "Bob" in stdout

    def test_missing_args_exits_nonzero(self):
        code, stdout, stderr = self.run_cli([])
        assert code != 0

    def test_help_exits_zero(self):
        code, stdout, stderr = self.run_cli(["--help"])
        assert code == 0

    def test_unsupported_format_prints_error(self):
        code, stdout, stderr = self.run_cli(["file.unknown", "output.json"])
        assert code == 1
        assert "Error:" in stderr


class TestVerboseFlag:
    def test_verbose_sets_debug_level(self):
        basic_configSpy = mock.patch("dataconv.cli.logging.basicConfig")
        with basic_configSpy as mock_basic:
            with mock.patch("dataconv.cli.Converter"):
                sys.argv = ["dataconv", "json", "csv", "--verbose"]
                main()

        mock_basic.assert_called()
        call_kwargs = mock_basic.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG

    def test_without_verbose_sets_warning_level(self):
        basic_configSpy = mock.patch("dataconv.cli.logging.basicConfig")
        with basic_configSpy as mock_basic:
            with mock.patch("dataconv.cli.Converter"):
                sys.argv = ["dataconv", "json", "csv"]
                main()

        mock_basic.assert_called()
        call_kwargs = mock_basic.call_args[1]
        assert call_kwargs["level"] == logging.WARNING
