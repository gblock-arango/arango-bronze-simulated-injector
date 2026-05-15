"""UC-backed playback cursor and play/stop flag (survives worker restarts)."""

from __future__ import annotations

import logging

from bronze_injector.services.databricks_sql import execute_sql, scalar_int
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)


def ensure_playback_state_table(table_name: str, warehouse_id: str) -> None:
    ref = parse_table_name(table_name)
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{ref.catalog}`.`{ref.schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                dataset_key STRING NOT NULL,
                last_row_idx BIGINT NOT NULL,
                is_playing BOOLEAN NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            USING DELTA
        """,
        warehouse_id=warehouse_id,
    )
    try:
        execute_sql(
            statement=f"GRANT SELECT, MODIFY ON TABLE {ref.fqn} TO `account users`",
            warehouse_id=warehouse_id,
        )
    except Exception as exc:
        logger.info("Could not grant playback state table: %s", exc)


def _safe_key(dataset_key: str) -> str:
    return (dataset_key or "").replace("'", "''")


def get_state(*, table_name: str, warehouse_id: str, dataset_key: str) -> dict:
    ref = parse_table_name(table_name)
    key = _safe_key(dataset_key)
    result = execute_sql(
        statement=f"""
            SELECT last_row_idx, is_playing, updated_at
            FROM {ref.fqn}
            WHERE dataset_key = '{key}'
            LIMIT 1
        """,
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    if not rows:
        return {"last_row_idx": 0, "is_playing": False, "updated_at": None}
    row = rows[0]
    return {
        "last_row_idx": int(row.get("last_row_idx") or 0),
        "is_playing": bool(row.get("is_playing")),
        "updated_at": row.get("updated_at"),
    }


def upsert_state(
    *,
    table_name: str,
    warehouse_id: str,
    dataset_key: str,
    last_row_idx: int | None = None,
    is_playing: bool | None = None,
) -> dict:
    ensure_playback_state_table(table_name, warehouse_id)
    current = get_state(
        table_name=table_name, warehouse_id=warehouse_id, dataset_key=dataset_key
    )
    idx = current["last_row_idx"] if last_row_idx is None else int(last_row_idx)
    playing = current["is_playing"] if is_playing is None else bool(is_playing)
    ref = parse_table_name(table_name)
    key = _safe_key(dataset_key)
    execute_sql(
        statement=f"""
            MERGE INTO {ref.fqn} t
            USING (
                SELECT
                    '{key}' AS dataset_key,
                    {idx} AS last_row_idx,
                    {str(playing).lower()} AS is_playing,
                    current_timestamp() AS updated_at
            ) s
            ON t.dataset_key = s.dataset_key
            WHEN MATCHED THEN UPDATE SET
                last_row_idx = s.last_row_idx,
                is_playing = s.is_playing,
                updated_at = s.updated_at
            WHEN NOT MATCHED THEN INSERT *
        """,
        warehouse_id=warehouse_id,
    )
    return get_state(table_name=table_name, warehouse_id=warehouse_id, dataset_key=dataset_key)


def max_row_idx_in_source(*, source_table: str, warehouse_id: str) -> int:
    ref = parse_table_name(source_table)
    result = execute_sql(
        statement=f"SELECT coalesce(max(_row_idx), -1) AS mx FROM {ref.fqn}",
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    if not rows:
        return -1
    return int(rows[0].get("mx", -1))
