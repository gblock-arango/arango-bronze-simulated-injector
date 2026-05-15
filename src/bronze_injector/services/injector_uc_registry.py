"""Publish this app's public URL and operational status to UC (arango_bronze_simulated_injector_registry)."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from databricks.sdk import WorkspaceClient

from bronze_injector.services.databricks_sql import execute_sql
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)

_publish_lock = threading.Lock()

_DELTA_CONCURRENT_MARKERS = (
    "concurrent",
    "concurrentappend",
    "concurrentmodification",
    "concurrent_append",
    "concurrent_modification",
    "concurrent_delete_read",
    "concurrent_delete_delete",
    "concurrent_transaction",
    "concurrent_write",
)


def _looks_like_delta_concurrent_conflict(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _DELTA_CONCURRENT_MARKERS)


def _sql_str(value: str) -> str:
    return (value or "").replace("'", "''")


def _sql_literal_string_or_null(value: str | None, *, null_if_empty: bool = True) -> str:
    if value is None or (null_if_empty and value == ""):
        return "CAST(NULL AS STRING)"
    return f"'{_sql_str(value)}'"


def ensure_injector_registry_table(table_name: str, warehouse_id: str) -> None:
    """Create UC table if missing (same MERGE semantics as gateway / arango-agent registries)."""
    ref = parse_table_name(table_name)
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{ref.catalog}`.`{ref.schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                base_url STRING NOT NULL,
                app_name STRING NOT NULL,
                is_active BOOLEAN NOT NULL,
                status STRING NOT NULL,
                playback_status STRING,
                dataset_key STRING,
                status_detail STRING,
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
        logger.info(
            "Could not GRANT injector registry to `account users` (may be disabled): %s",
            exc,
        )


def merge_injector_registry_row(
    *,
    table_name: str,
    warehouse_id: str,
    base_url: str,
    app_name: str,
    status: str,
    playback_status: str | None,
    dataset_key: str | None,
    status_detail: str | None,
    max_merge_retries: int = 8,
) -> None:
    """
    Upsert active row for this app's URL; deactivate other rows (same ON base_url pattern as agent).
    """
    url = (base_url or "").strip().rstrip("/")
    name = (app_name or "").strip()
    if not url or not name:
        return
    ref = parse_table_name(table_name)
    pb = playback_status if playback_status is not None else "IDLE"
    ds = dataset_key if dataset_key is not None else ""
    st = status or "UNKNOWN"
    det_sql = _sql_literal_string_or_null(status_detail, null_if_empty=True)

    merge_sql = f"""
        MERGE INTO {ref.fqn} t
        USING (
            SELECT
                '{_sql_str(url)}' AS base_url,
                '{_sql_str(name)}' AS app_name,
                '{_sql_str(st)}' AS status,
                '{_sql_str(pb)}' AS playback_status,
                '{_sql_str(ds)}' AS dataset_key,
                {det_sql} AS status_detail,
                current_timestamp() AS updated_at
        ) s
        ON t.base_url = s.base_url
        WHEN MATCHED THEN UPDATE SET
            app_name = s.app_name,
            is_active = TRUE,
            status = s.status,
            playback_status = s.playback_status,
            dataset_key = s.dataset_key,
            status_detail = s.status_detail,
            updated_at = s.updated_at
        WHEN NOT MATCHED THEN INSERT
            (base_url, app_name, is_active, status, playback_status, dataset_key,
             status_detail, updated_at)
            VALUES (
                s.base_url, s.app_name, TRUE,
                s.status, s.playback_status, s.dataset_key, s.status_detail, s.updated_at
            )
        WHEN NOT MATCHED BY SOURCE AND t.is_active = TRUE THEN UPDATE SET
            is_active = FALSE,
            updated_at = current_timestamp()
    """

    last_exc: Exception | None = None
    for attempt in range(1, max(1, max_merge_retries) + 1):
        try:
            execute_sql(statement=merge_sql, warehouse_id=warehouse_id)
            try:
                execute_sql(
                    statement=(
                        f"GRANT SELECT, MODIFY ON TABLE {ref.fqn} TO `account users`"
                    ),
                    warehouse_id=warehouse_id,
                )
            except Exception as grant_exc:
                logger.info(
                    "Could not GRANT injector registry after MERGE (`account users`): %s",
                    grant_exc,
                )
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= max_merge_retries or not _looks_like_delta_concurrent_conflict(exc):
                raise
            backoff = 0.25 * attempt
            logger.warning(
                "Concurrent MERGE on %s attempt %s/%s; backoff %.2fs: %s",
                ref.fqn,
                attempt,
                max_merge_retries,
                backoff,
                exc,
            )
            time.sleep(backoff)
    if last_exc is not None:
        raise last_exc


def patch_injector_registry_row(
    *,
    table_name: str,
    warehouse_id: str,
    base_url: str,
    status: str | None = None,
    playback_status: str | None = None,
    status_detail: str | None = None,
    dataset_key: str | None = None,
    app_name: str | None = None,
) -> None:
    """Partial UPDATE for this base_url (playback without clobbering lifecycle status)."""
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return
    ref = parse_table_name(table_name)
    sets: list[str] = []
    if status is not None:
        sets.append(f"status = '{_sql_str(status)}'")
    if playback_status is not None:
        sets.append(f"playback_status = '{_sql_str(playback_status)}'")
    if dataset_key is not None:
        sets.append(f"dataset_key = '{_sql_str(dataset_key)}'")
    if status_detail is not None:
        sets.append(f"status_detail = {_sql_literal_string_or_null(status_detail)}")
    if app_name is not None:
        sets.append(f"app_name = '{_sql_str(app_name)}'")
    if not sets:
        return
    sets.append("updated_at = current_timestamp()")
    sql = f"UPDATE {ref.fqn} SET {', '.join(sets)} WHERE base_url = '{_sql_str(url)}'"
    execute_sql(statement=sql, warehouse_id=warehouse_id)


def resolve_self_app_base_url() -> str | None:
    name = (os.environ.get("DATABRICKS_APP_NAME") or "").strip()
    if not name:
        return None
    try:
        app = WorkspaceClient().apps.get(name)
        u = (getattr(app, "url", None) or "").strip().rstrip("/")
        return u or None
    except Exception as exc:
        logger.warning("Could not resolve Databricks App URL for %r: %s", name, exc)
        return None


def publish_self_injector_registry_if_configured(flask_app: Any) -> None:
    """On startup: ensure table + upsert STARTING row if auto-create enabled."""
    if not bool(
        flask_app.config.get("ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_AUTO_CREATE", True)
    ):
        return
    table = str(
        flask_app.config.get("ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE") or ""
    ).strip()
    warehouse = str(flask_app.config.get("DATABRICKS_SQL_WAREHOUSE_ID") or "").strip()
    if not table or not warehouse:
        return
    url = resolve_self_app_base_url()
    if not url:
        return
    app_name = (os.environ.get("DATABRICKS_APP_NAME") or "").strip() or "unknown"

    try:
        with _publish_lock:
            ensure_injector_registry_table(table, warehouse)
            from bronze_injector.config import config_from_flask

            cfg = config_from_flask(flask_app.config)
            merge_injector_registry_row(
                table_name=table,
                warehouse_id=warehouse,
                base_url=url,
                app_name=app_name,
                status="STARTING",
                playback_status="IDLE",
                dataset_key=cfg.dataset_key(),
                status_detail="app_boot",
            )
        logger.info("Published bronze injector registry (STARTING) to %s", table)
    except Exception as exc:
        logger.warning("Could not publish bronze injector registry (%s): %s", table, exc)


def update_injector_registry_status(
    flask_app: Any,
    *,
    status: str | None = None,
    playback_status: str | None = None,
    status_detail: str | None = None,
    dataset_key: str | None = None,
    use_merge: bool = False,
) -> None:
    """
    Update registry row for this app URL.

    Default: PATCH (only columns that are not None). Set ``use_merge=True`` for a full upsert
    with defaults (e.g. first publish).
    """
    if not bool(
        flask_app.config.get("ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_AUTO_CREATE", True)
    ):
        return
    table = str(
        flask_app.config.get("ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE") or ""
    ).strip()
    warehouse = str(flask_app.config.get("DATABRICKS_SQL_WAREHOUSE_ID") or "").strip()
    if not table or not warehouse:
        return
    url = resolve_self_app_base_url()
    if not url:
        return
    app_name = (os.environ.get("DATABRICKS_APP_NAME") or "").strip() or "unknown"

    from bronze_injector.config import config_from_flask

    cfg = config_from_flask(flask_app.config)
    if use_merge:
        merge_injector_registry_row(
            table_name=table,
            warehouse_id=warehouse,
            base_url=url,
            app_name=app_name,
            status=status or "READY",
            playback_status=playback_status,
            dataset_key=dataset_key if dataset_key is not None else cfg.dataset_key(),
            status_detail=status_detail,
            max_merge_retries=6,
        )
        return

    patch_injector_registry_row(
        table_name=table,
        warehouse_id=warehouse,
        base_url=url,
        status=status,
        playback_status=playback_status,
        status_detail=status_detail,
        dataset_key=dataset_key,
    )
