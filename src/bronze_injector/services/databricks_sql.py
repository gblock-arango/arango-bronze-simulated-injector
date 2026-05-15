"""Databricks SQL Statement Execution API helpers."""

from __future__ import annotations

from databricks.sdk import WorkspaceClient


def execute_sql(statement: str, warehouse_id: str) -> dict:
    workspace_client = WorkspaceClient()
    response = workspace_client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="50s",
    )

    raw_status = response.status.state if response.status else None
    status = str(raw_status) if raw_status is not None else ""
    if status and not status.endswith("SUCCEEDED"):
        err = response.status.error.message if response.status.error else "unknown error"
        raise RuntimeError(f"Databricks SQL failed ({status}): {err}")

    if not response.manifest or not response.manifest.schema:
        return {"columns": [], "rows": []}

    columns = [col.name for col in response.manifest.schema.columns]
    rows = []
    if response.result and response.result.data_array:
        for row in response.result.data_array:
            rows.append(dict(zip(columns, row)))
    return {"columns": columns, "rows": rows}


def scalar_int(result: dict, column: str = "cnt", default: int = 0) -> int:
    rows = result.get("rows") or []
    if not rows:
        return default
    val = rows[0].get(column, default)
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
