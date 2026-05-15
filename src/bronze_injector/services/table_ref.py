"""Parse Unity Catalog three-part table names."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableRef:
    catalog: str
    schema: str
    table: str

    @property
    def fqn(self) -> str:
        return f"`{self.catalog}`.`{self.schema}`.`{self.table}`"


def parse_table_name(table_name: str) -> TableRef:
    parts = (table_name or "").strip().split(".")
    if len(parts) != 3 or any(not p.strip() for p in parts):
        raise ValueError("Table name must be catalog.schema.table")
    return TableRef(catalog=parts[0], schema=parts[1], table=parts[2])
