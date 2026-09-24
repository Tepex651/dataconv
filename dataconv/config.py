"""Configuration — behavioral settings for the converter."""

from dataclasses import dataclass
from enum import Enum


class CsvKeys(Enum):
    """CSV column naming strategy."""

    dotted = "dotted"   # address.city
    flat = "flat"   # city


@dataclass
class Config:
    flatten: bool = False
    csv_keys: CsvKeys = CsvKeys.dotted
    xml_root: str = "rows"
    xml_item: str = "row"
