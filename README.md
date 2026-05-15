# dataconv

Convert data files between formats with optional Pydantic validation.

**Supported formats:** JSON, CSV

## Install

```bash
pip install -e .
```

Or with uv:

```bash
uv run dataconv ...
```

## Usage

### Basic conversion

```bash
dataconv input.json output.csv
dataconv input.csv output.json
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
dataconv INPUT OUTPUT [OPTIONS]

Positional arguments:
  input              Input file path (.json or .csv)
  output             Output file path (.json or .csv)

Options:
  --schema PATH      Path to Pydantic schema file for validation
  -e, --errors PATH  Path to write invalid rows to
  -h, --help         Show this help message
```

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
