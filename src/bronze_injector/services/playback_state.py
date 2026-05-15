"""UC-backed playback cursor, opaque file/chunk marker, and play/stop flag."""

from __future__ import annotations

import logging

from bronze_injector.services.databricks_sql import execute_sql
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
                playback_file_marker STRING,
                updated_at TIMESTAMP NOT NULL
            )
            USING DELTA
        """,
        warehouse_id=warehouse_id,
    )
    try:
        execute_sql(
            statement=(
                f"ALTER TABLE {ref.fqn} ADD COLUMN playback_file_marker STRING"
            ),
            warehouse_id=warehouse_id,
        )
    except Exception as exc:
        logger.debug(
            "playback_file_marker column add skipped or unsupported: %s", exc
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
            SELECT last_row_idx, is_playing, playback_file_marker, updated_at
            FROM {ref.fqn}
            WHERE dataset_key = '{key}'
            LIMIT 1
        """,
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    if not rows:
        return {
            "last_row_idx": -1,
            "is_playing": False,
            "playback_file_marker": None,
            "updated_at": None,
        }
    row = rows[0]
    raw_idx = row.get("last_row_idx")
    return {
        "last_row_idx": -1 if raw_idx is None else int(raw_idx),
        "is_playing": bool(row.get("is_playing")),
        "playback_file_marker": row.get("playback_file_marker"),
        "updated_at": row.get("updated_at"),
    }


def upsert_state(
    *,
    table_name: str,
    warehouse_id: str,
    dataset_key: str,
    last_row_idx: int | None = None,
    is_playing: bool | None = None,
    playback_file_marker: str | None = None,
    update_playback_file_marker: bool = False,
) -> dict:
    """Persist playback row. Set ``update_playback_file_marker=True`` to write ``playback_file_marker`` (including NULL)."""
    ensure_playback_state_table(table_name, warehouse_id)
    current = get_state(
        table_name=table_name, warehouse_id=warehouse_id, dataset_key=dataset_key
    )
    idx = current["last_row_idx"] if last_row_idx is None else int(last_row_idx)
    playing = current["is_playing"] if is_playing is None else bool(is_playing)
    marker_expr: str
    if update_playback_file_marker:
        if playback_file_marker is None:
            marker_expr = "CAST(NULL AS STRING)"
        else:
            esc = str(playback_file_marker).replace("'", "''")
            marker_expr = f"CAST('{esc}' AS STRING)"
    else:
        m = current["playback_file_marker"]
        if m is None:
            marker_expr = "CAST(NULL AS STRING)"
        else:
            esc = str(m).replace("'", "''")
            marker_expr = f"CAST('{esc}' AS STRING)"

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
                    {marker_expr} AS playback_file_marker,
                    current_timestamp() AS updated_at
            ) s
            ON t.dataset_key = s.dataset_key
            WHEN MATCHED THEN UPDATE SET
                last_row_idx = s.last_row_idx,
                is_playing = s.is_playing,
                playback_file_marker = s.playback_file_marker,
                updated_at = s.updated_at
            WHEN NOT MATCHED THEN INSERT *
        """,
        warehouse_id=warehouse_id,
    )
    return get_state(table_name=table_name, warehouse_id=warehouse_id, dataset_key=dataset_key)


def max_row_idx_for_dataset(
    *, bronze_table: str, warehouse_id: str, dataset_key: str
) -> int:
    """Maximum ``_row_idx`` present in bronze for this dataset (inclusive)."""
    ref = parse_table_name(bronze_table)
    dk = _safe_key(dataset_key)
    result = execute_sql(
        statement=(
            f"SELECT coalesce(max(_row_idx), -1) AS mx FROM {ref.fqn} "
            f"WHERE dataset_key = '{dk}'"
        ),
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    if not rows:
        return -1
    return int(rows[0].get("mx", -1))


def max_fresh_row_idx_for_dataset(
    *, bronze_table: str, warehouse_id: str, dataset_key: str
) -> int:
    ref = parse_table_name(bronze_table)
    dk = _safe_key(dataset_key)
    result = execute_sql(
        statement=(
            f"SELECT coalesce(max(_row_idx), -1) AS mx FROM {ref.fqn} "
            f"WHERE dataset_key = '{dk}' AND freshness = 'fresh'"
        ),
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    if not rows:
        return -1
    return int(rows[0].get("mx", -1))
