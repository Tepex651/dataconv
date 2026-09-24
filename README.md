# dataconv

Convert data files between formats with optional Pydantic validation.

**Supported formats:** JSON, CSV, NDJSON (JSONL), YAML, XML

## Install

```bash
pip install -e .
```

Or with uv:

```bash
uv run dataconv ...
```

### Optional dependencies

- **PyYAML** — for YAML support: `pip install pyyaml`
- **Dev tools** — for testing: `pip install -e ".[dev]"`

## Usage

### Basic conversion

```bash
dataconv input.json output.csv
dataconv input.csv output.json
```

Format is auto-detected from file extensions.

### Streaming via stdin/stdout

Use format names instead of file paths to read from stdin / write to stdout:

```bash
# Read JSON from stdin, write CSV to stdout
cat input.json | dataconv json csv

# Read file, write to stdout
dataconv input.json csv | less

# Read from stdin, write to file
cat input.json | dataconv json output.csv

# Chain conversions
cat data.json | dataconv json ndjson | dataconv ndjson yaml
```

### With schema validation

```bash
dataconv input.json output.csv --schema examples/schema.py
```

Rows that fail validation are excluded from the output file.

### With error output

```bash
dataconv examples/input.json output.csv --schema examples/schema.py --errors errors.json
```

Invalid rows are written to `errors.json` alongside validation error messages.

### Verbose mode

```bash
dataconv input.json output.csv --verbose
```

Shows warnings for schema load failures, validation errors, and key collisions.

## Schema file

A schema is a Python file defining a Pydantic model:

```python
from pydantic import BaseModel

class RowSchema(BaseModel):
    id: int
    name: str
    email: str
```

The first `BaseModel` subclass found in the file will be used for validation.

### Nested data

For nested JSON structures you can use nested Pydantic models:

```python
from pydantic import BaseModel

class RowSchema(BaseModel):
    class Address(BaseModel):
        city: str | None = None
        zip: str | None = ""

    id: int
    name: str
    email: str
    age: int
    active: bool
    address: Address | None = None
```

See [`examples/schema.py`](examples/schema.py) for a full example matching the sample data.

### Flat data (CSV)

CSV files use flat dotted keys like `address.city`. Match them with a flat schema:

```python
from pydantic import BaseModel

class RowSchema(BaseModel):
    id: int
    name: str
    email: str
    age: int
    active: bool
    address_city: str | None = ""
    address_zip: str | None = ""
```

## CLI reference

```
dataconv [INPUT] [OUTPUT] [OPTIONS]

Positional arguments:
   input              Input file path (.json, .csv, .ndjson, .yaml, .xml) or format name (json, csv, ndjson, yaml, xml) for stdin
  output             Output file path or format name for stdout

Options:
    --schema PATH      Path to Pydantic schema file for validation
    -e, --errors PATH  Path to write invalid rows to
    --flatten          Flatten nested objects in output (default: keep nested)
     --csv-keys FMT     CSV column naming: dotted=address.city (default), flat=city
      --xml-root NAME   XML wrapper element for output (default: rows)
      --xml-item NAME   XML row element for output (default: row)
      -v, --verbose      Show warnings and debug info
      -h, --help         Show this help message
```

### Positional argument combinations

| Command | Input | Output |
|---|---|---|
| `dataconv input.json output.csv` | file → file | file |
| `dataconv input.json csv` | file | stdout (csv) |
| `dataconv json output.csv` | stdin (json) | file |
| `dataconv json csv` | stdin (json) | stdout (csv) |
| `dataconv input.json` | file | stdout (format guessed from input) |

## Format details

### JSON (`.json`)
Full JSON arrays or objects. Nested data is preserved on write.

### CSV (`.csv`)
Flat tabular data. Nested JSON is automatically flattened using dot-separated keys (e.g., `address.city`). Column order follows first-seen insertion order.

### NDJSON / JSONL (`.ndjson`, `.jsonl`)
One JSON object per line. Comments (lines starting with `#`) are ignored. Malformed lines are skipped with a warning.

### YAML (`.yaml`, `.yml`)
Full YAML documents or streams. Requires `pyyaml` installed.

### XML (`.xml`)
Nested records wrapped as `<rows><row>…</row></rows>` by default — one `<row>`
element per record. Fields become child elements; repeated tags collapse to a
list, and nested dictionaries recurse into nested elements. Namespaces are
stripped and attribute names are merged under an `@` prefix. Reads are strings
(like CSV), so type coercion (int/bool) only happens when a schema is supplied.
Requires no extra dependency (uses the stdlib `xml.etree` module).

**On read** the wrapper is auto-detected: a root whose children are all the same
element (e.g. `<users><user>…</user></users>`) is unwrapped into rows, while a
root with heterogeneous children (e.g. `<person><name/><address/></person>`) is
treated as a single nested record.

**On write** the wrapper names are fixed at `rows`/`row` unless overridden with
`--xml-root` / `--xml-item` (e.g. `--xml-root users --xml-item user` produces
`<users><user>…</user></users>`).


## Examples

Convert JSON to CSV:

```bash
dataconv examples/input.json output.csv
```

Convert JSON to CSV with validation:

```bash
dataconv examples/input.json output.csv --schema examples/schema.py
```

Convert CSV to JSON with validation and error output:

```bash
dataconv examples/input.csv output.json --schema examples/schema.py --errors errors.json
```

Stream JSON through to CSV:

```bash
cat examples/input.json | dataconv json csv
```

Convert YAML to NDJSON:

```bash
dataconv data.yaml output.ndjson
```

Convert XML to JSON:

```bash
dataconv data.xml output.json
```

Write XML with a custom entity name:

```bash
dataconv data.json data.xml --xml-root users --xml-item user
```

