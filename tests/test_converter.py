"""Tests for dataconv — core conversion logic."""

import io
import json
from unittest import mock

import pytest

from dataconv.config import Config, CsvKeys
from dataconv.converter import Converter
from dataconv.formats.base import get_handler, registered_formats
from dataconv.formats.csv import CSVFormat
from dataconv.formats.json import JSONFormat
from dataconv.formats.ndjson import NDJSONFormat
from dataconv.formats.xml import XMLFormat
from dataconv.formats.yaml import YAMLFormat
from dataconv.utils import UnsupportedFormatError


@pytest.fixture
def sample_data():
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ]


@pytest.fixture
def nested_data():
    return [
        {"id": 1, "name": "Alice", "address": {"city": "NYC", "zip": "10001"}},
        {"id": 2, "name": "Bob", "address": None},
    ]


class TestJSONRoundtrip:
    def test_json_to_json(self, sample_data, tmp_path):
        inp = tmp_path / "input.json"
        out = tmp_path / "output.json"
        inp.write_text(json.dumps(sample_data))
        Converter(inp, out).run()
        with open(out) as f:
            assert json.load(f) == sample_data

    def test_json_to_csv(self, sample_data, tmp_path):
        inp = tmp_path / "input.json"
        out = tmp_path / "output.csv"
        inp.write_text(json.dumps(sample_data))
        Converter(inp, out).run()
        text = out.read_text()
        assert "id,name,email" in text
        assert "Alice" in text

    def test_csv_to_json(self, sample_data, tmp_path):
        inp = tmp_path / "input.csv"
        out = tmp_path / "output.json"
        inp.write_text("id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n")
        Converter(inp, out).run()
        with open(out) as f:
            result = json.load(f)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"


class TestNestedData:
    def test_json_nested_flattens_to_csv(self, nested_data, tmp_path):
        inp = tmp_path / "input.json"
        out = tmp_path / "output.csv"
        inp.write_text(json.dumps(nested_data))
        Converter(inp, out).run()
        text = out.read_text()
        assert "address.city" in text
        assert "NYC" in text

    def test_csv_to_json_preserves_flat_keys(self, tmp_path):
        inp = tmp_path / "input.csv"
        out = tmp_path / "output.json"
        inp.write_text("id,address_city\n1,NYC\n2,\n")
        Converter(inp, out).run()
        with open(out) as f:
            result = json.load(f)
        assert result[0]["address_city"] == "NYC"


class TestValidation:
    def _write_schema(self, path, fields):
        lines = ["from pydantic import BaseModel", "class RowSchema(BaseModel):"]
        for f in fields:
            lines.append(f"    {f}")
        path.write_text("\n".join(lines) + "\n")

    def test_valid_rows_pass(self, sample_data, tmp_path):
        schema_file = tmp_path / "schema.py"
        self._write_schema(schema_file, ["id: int", "name: str"])
        inp = tmp_path / "input.json"
        out = tmp_path / "output.json"
        inp.write_text(json.dumps(sample_data))
        Converter(inp, out, schema_path=schema_file).run()
        with open(out) as f:
            result = json.load(f)
        assert len(result) == 2

    def test_invalid_rows_excluded(self, tmp_path):
        data = [{"id": 1, "name": "Alice"}, {"id": "not_an_int", "name": "Bob"}]
        schema_file = tmp_path / "schema.py"
        self._write_schema(schema_file, ["id: int", "name: str"])
        inp = tmp_path / "input.json"
        out = tmp_path / "output.json"
        inp.write_text(json.dumps(data))
        Converter(inp, out, schema_path=schema_file).run()
        with open(out) as f:
            result = json.load(f)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_errors_file_captures_invalid_rows(self, tmp_path):
        data = [{"id": 1, "name": "Alice"}, {"id": "bad", "name": "Bob"}]
        schema_file = tmp_path / "schema.py"
        self._write_schema(schema_file, ["id: int", "name: str"])
        inp = tmp_path / "input.json"
        out = tmp_path / "output.json"
        errors = tmp_path / "errors.json"
        inp.write_text(json.dumps(data))
        Converter(inp, out, schema_path=schema_file, error_path=errors).run()
        with open(errors) as f:
            errs = json.load(f)
        assert len(errs) == 1
        assert errs[0]["data"]["name"] == "Bob"


class TestKeyTruncation:
    def test_truncate_avoids_collisions(self, tmp_path):
        """csv_keys=flat truncates dotted keys to last segment in CSV output."""
        data = [{"user": {"name": "Alice", "addr": "NYC"}}]
        inp = tmp_path / "input.json"
        out = tmp_path / "output.csv"
        inp.write_text(json.dumps(data))
        Converter(inp, out, config=Config(csv_keys=CsvKeys.flat)).run()
        text = out.read_text()
        assert "name" in text
        assert "addr" in text


class TestStdinStdout:
    def test_read_stdin_json(self, sample_data):
        result = JSONFormat().read_stdin(io.StringIO(json.dumps(sample_data)))
        assert result == sample_data

    def test_write_stdout_json(self, sample_data):
        buf = io.StringIO()
        JSONFormat().write_stdout(buf, sample_data)
        buf.seek(0)
        assert json.load(buf) == sample_data

    def test_read_stdin_csv(self):
        result = CSVFormat().read_stdin(io.StringIO("id,name\n1,Alice\n2,Bob\n"))
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_write_stdout_csv(self, sample_data):
        buf = io.StringIO()
        CSVFormat().write_stdout(buf, sample_data)
        buf.seek(0)
        text = buf.read()
        assert "id,name,email" in text
        assert "Alice" in text


class TestNDJSON:
    def test_read_ndjson(self, tmp_path):
        inp = tmp_path / "input.ndjson"
        inp.write_text('{"id":1,"name":"Alice"}\n{"id":2,"name":"Bob"}\n')
        result = NDJSONFormat().read(inp)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_write_ndjson(self, sample_data, tmp_path):
        out = tmp_path / "output.ndjson"
        NDJSONFormat().write(out, sample_data)
        lines = [line for line in out.read_text().strip().split("\n") if line]
        assert len(lines) == 2
        assert json.loads(lines[0])["name"] == "Alice"

    def test_skips_comments_and_malformed_lines(self, tmp_path):
        inp = tmp_path / "input.ndjson"
        inp.write_text('# comment\n{"id":1}\nbad json\n{"id":2}\n')
        result = NDJSONFormat().read(inp)
        assert len(result) == 2

    def test_read_stdin_ndjson(self):
        result = NDJSONFormat().read_stdin(io.StringIO('{"id":1}\n{"id":2}\n'))
        assert len(result) == 2

    def test_write_stdout_ndjson(self, sample_data):
        buf = io.StringIO()
        NDJSONFormat().write_stdout(buf, sample_data)
        buf.seek(0)
        lines = [line for line in buf.read().strip().split("\n") if line]
        assert len(lines) == 2


class TestYAML:
    def test_read_yaml(self, tmp_path):
        inp = tmp_path / "input.yaml"
        inp.write_text("- id: 1\n  name: Alice\n- id: 2\n  name: Bob\n")
        result = YAMLFormat().read(inp)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_write_yaml(self, sample_data, tmp_path):
        out = tmp_path / "output.yaml"
        YAMLFormat().write(out, sample_data)
        text = out.read_text()
        assert "Alice" in text
        assert "Bob" in text

    def test_read_stdin_yaml(self):
        result = YAMLFormat().read_stdin(io.StringIO("- id: 1\n  name: Alice\n"))
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_write_stdout_yaml(self, sample_data):
        buf = io.StringIO()
        YAMLFormat().write_stdout(buf, sample_data)
        buf.seek(0)
        text = buf.read()
        assert "Alice" in text


class TestXML:
    def _doc(self) -> str:
        return (
            "<rows>\n"
            "  <row>\n"
            "    <id>1</id>\n"
            "    <name>Alice</name>\n"
            "    <address>\n"
            "      <city>NYC</city>\n"
            "      <zip>10001</zip>\n"
            "    </address>\n"
            "  </row>\n"
            "  <row>\n"
            "    <id>2</id>\n"
            "    <name>Bob</name>\n"
            "  </row>\n"
            "</rows>\n"
        )

    def test_read_xml(self, tmp_path):
        inp = tmp_path / "input.xml"
        inp.write_text(self._doc())
        result = XMLFormat().read(inp)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["address"]["city"] == "NYC"

    def test_write_xml(self, sample_data, tmp_path):
        out = tmp_path / "output.xml"
        XMLFormat().write(out, sample_data)
        text = out.read_text()
        assert "Alice" in text
        assert "Bob" in text

    def test_roundtrip(self, sample_data, tmp_path):
        out = tmp_path / "output.xml"
        XMLFormat().write(out, sample_data)
        result = XMLFormat().read(out)
        assert [r["name"] for r in result] == ["Alice", "Bob"]

    def test_repeated_tag_becomes_list(self, tmp_path):
        inp = tmp_path / "input.xml"
        inp.write_text("<rows><row><tag>a</tag><tag>b</tag></row></rows>\n")
        result = XMLFormat().read(inp)
        assert result[0]["tag"] == ["a", "b"]

    def test_invalid_tag_name_sanitized(self, tmp_path):
        out = tmp_path / "output.xml"
        XMLFormat().write(out, [{"key with space": "a", "a+b": "b", "9lives": 9}])
        text = out.read_text()
        assert "key_with_space" in text
        assert "a_b" in text
        assert "_9lives" in text

    def test_empty_input(self):
        assert XMLFormat().read_stdin(io.StringIO("")) == []

    def test_read_stdin_xml(self):
        result = XMLFormat().read_stdin(io.StringIO("<rows><row><name>Alice</name></row></rows>"))
        assert result[0]["name"] == "Alice"

    def test_write_stdout_xml(self, sample_data):
        buf = io.StringIO()
        XMLFormat().write_stdout(buf, sample_data)
        buf.seek(0)
        text = buf.read()
        assert "Alice" in text

    def test_read_autodetect_heterogeneous_root(self):
        """A single nested record (mixed children) is one row, not unwrapped."""
        xml_in = "<person><name>Alice</name><address><city>NYC</city></address></person>"
        result = XMLFormat().read_stdin(io.StringIO(xml_in))
        assert result == [{"name": "Alice", "address": {"city": "NYC"}}]

    def test_read_autodetect_entity_root(self):
        """Non-rows wrapper with uniform children is unwrapped into rows."""
        xml_in = "<users><user><name>Alice</name></user><user><name>Bob</name></user></users>"
        result = XMLFormat().read_stdin(io.StringIO(xml_in))
        assert [r["name"] for r in result] == ["Alice", "Bob"]

    def test_write_custom_root_item(self, sample_data, tmp_path):
        out = tmp_path / "output.xml"
        XMLFormat(config=Config(xml_root="users", xml_item="user")).write(out, sample_data)
        text = out.read_text()
        assert "<users>" in text
        assert "<user>" in text


class TestFormatRegistry:
    def test_registered_formats_includes_all(self):
        fmts = registered_formats()
        assert ".json" in fmts
        assert ".csv" in fmts
        assert ".ndjson" in fmts
        assert ".yaml" in fmts
        assert ".xml" in fmts

    def test_get_handler_by_extension(self):
        assert isinstance(get_handler(".json"), JSONFormat)
        assert isinstance(get_handler(".csv"), CSVFormat)
        assert isinstance(get_handler(".xml"), XMLFormat)

    def test_unsupported_format_raises(self):
        with pytest.raises(UnsupportedFormatError):
            get_handler(".xyz")


class TestConverterStdinStdout:
    """Integration tests: Converter routes stdin/stdout to handler methods."""

    def test_converter_reads_stdin(self, sample_data, tmp_path):
        """Converter with format name for input reads from stdin."""
        out = tmp_path / "output.json"
        conv = Converter("json", out)
        with mock.patch("sys.stdin", io.StringIO(json.dumps(sample_data))):
            conv.run()
        with open(out) as f:
            result = json.load(f)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_converter_writes_stdout(self, sample_data, tmp_path):
        """Converter with format name for output writes to stdout."""
        inp = tmp_path / "input.json"
        inp.write_text(json.dumps(sample_data))
        conv = Converter(inp, "csv")
        stdout_buf = io.StringIO()
        with mock.patch("sys.stdout", stdout_buf):
            conv.run()
        text = stdout_buf.getvalue()
        assert "id,name,email" in text
        assert "Alice" in text

    def test_converter_stdin_to_stdout(self, sample_data):
        """Full pipe: stdin JSON to stdout JSON."""
        conv = Converter("json", "json")
        stdin_buf = io.StringIO(json.dumps(sample_data))
        stdout_buf = io.StringIO()
        with mock.patch("sys.stdin", stdin_buf):
            with mock.patch("sys.stdout", stdout_buf):
                conv.run()
        result = json.loads(stdout_buf.getvalue())
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_converter_no_fmt_raises(self):
        """Converter with unknown path raises ValueError."""
        conv = Converter("unknown.txt", "output.json")
        with pytest.raises(ValueError, match="Cannot detect format"):
            conv.run()

    def test_converter_stdin_csv_to_stdout_json(self):
        """stdin CSV to stdout JSON via Converter."""
        conv = Converter("csv", "json")
        stdin_buf = io.StringIO("id,name\n1,Alice\n2,Bob\n")
        stdout_buf = io.StringIO()
        with mock.patch("sys.stdin", stdin_buf):
            with mock.patch("sys.stdout", stdout_buf):
                conv.run()
        result = json.loads(stdout_buf.getvalue())
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
