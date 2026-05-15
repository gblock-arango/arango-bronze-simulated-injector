"""Background playback: stream test_bronze_data rows into bronze tables."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from bronze_injector.services.databricks_sql import execute_sql, scalar_int
from bronze_injector.services.dataset_loader import ensure_bronze_table
from bronze_injector.services.playback_state import (
    get_state,
    max_row_idx_in_source,
    upsert_state,
)
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)


class PlaybackController:
    """Single-process playback loop (use gunicorn --workers 1)."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._batch_id = 0

    def status_snapshot(self, cfg: dict[str, Any]) -> dict[str, Any]:
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        dataset_key = cfg["dataset_key"]
        state_table = cfg["PLAYBACK_STATE_TABLE"]
        source_table = cfg["test_source_table"]
        bronze_table = cfg["bronze_table"]
        state = get_state(
            table_name=state_table,
            warehouse_id=warehouse_id,
            dataset_key=dataset_key,
        )
        source_max = max_row_idx_in_source(
            source_table=source_table, warehouse_id=warehouse_id
        )
        ref = parse_table_name(bronze_table)
        bronze_count = scalar_int(
            execute_sql(
                statement=f"SELECT count(*) AS cnt FROM {ref.fqn}",
                warehouse_id=warehouse_id,
            ),
            "cnt",
            0,
        )
        with self._lock:
            thread_alive = self._thread is not None and self._thread.is_alive()
        return {
            "dataset_key": dataset_key,
            "is_playing": state["is_playing"] or thread_alive,
            "last_row_idx": state["last_row_idx"],
            "source_max_row_idx": source_max,
            "bronze_row_count": bronze_count,
            "source_table": source_table,
            "bronze_table": bronze_table,
            "thread_alive": thread_alive,
        }

    def play(self, cfg: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return {"ok": True, "message": "already_playing", **self.status_snapshot(cfg)}
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(cfg,),
                name="bronze-playback",
                daemon=True,
            )
            self._thread.start()
        upsert_state(
            table_name=cfg["PLAYBACK_STATE_TABLE"],
            warehouse_id=cfg["DATABRICKS_SQL_WAREHOUSE_ID"],
            dataset_key=cfg["dataset_key"],
            is_playing=True,
        )
        return {"ok": True, "message": "play_started", **self.status_snapshot(cfg)}

    def stop(self, cfg: dict[str, Any]) -> dict[str, Any]:
        self._stop_event.set()
        upsert_state(
            table_name=cfg["PLAYBACK_STATE_TABLE"],
            warehouse_id=cfg["DATABRICKS_SQL_WAREHOUSE_ID"],
            dataset_key=cfg["dataset_key"],
            is_playing=False,
        )
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout=5.0)
        return {"ok": True, "message": "stop_requested", **self.status_snapshot(cfg)}

    def reset(self, cfg: dict[str, Any]) -> dict[str, Any]:
        self.stop(cfg)
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        bronze_ref = parse_table_name(cfg["bronze_table"])
        execute_sql(
            statement=f"TRUNCATE TABLE {bronze_ref.fqn}",
            warehouse_id=warehouse_id,
        )
        upsert_state(
            table_name=cfg["PLAYBACK_STATE_TABLE"],
            warehouse_id=warehouse_id,
            dataset_key=cfg["dataset_key"],
            last_row_idx=0,
            is_playing=False,
        )
        return {"ok": True, "message": "reset_complete", **self.status_snapshot(cfg)}

    def _run_loop(self, cfg: dict[str, Any]) -> None:
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        dataset_key = cfg["dataset_key"]
        state_table = cfg["PLAYBACK_STATE_TABLE"]
        source_table = cfg["test_source_table"]
        bronze_table = cfg["bronze_table"]
        batch_size = int(cfg.get("PLAYBACK_BATCH_SIZE") or 200)
        interval = float(cfg.get("PLAYBACK_INTERVAL_SEC") or 0.25)

        ensure_bronze_table(bronze_table, warehouse_id)
        source_ref = parse_table_name(source_table)
        bronze_ref = parse_table_name(bronze_table)

        try:
            while not self._stop_event.is_set():
                state = get_state(
                    table_name=state_table,
                    warehouse_id=warehouse_id,
                    dataset_key=dataset_key,
                )
                start_idx = int(state["last_row_idx"])
                source_max = max_row_idx_in_source(
                    source_table=source_table, warehouse_id=warehouse_id
                )
                if start_idx > source_max:
                    upsert_state(
                        table_name=state_table,
                        warehouse_id=warehouse_id,
                        dataset_key=dataset_key,
                        is_playing=False,
                    )
                    logger.info("Playback reached end of source (idx=%s)", start_idx)
                    break

                self._batch_id += 1
                batch_id = self._batch_id
                execute_sql(
                    statement=f"""
                        INSERT INTO {bronze_ref.fqn}
                        (
                            _row_idx, record_type, tx_id, src_tx, dst_tx,
                            time_step, label, features_json, ingested_at,
                            playback_batch_id, bronze_ingested_at
                        )
                        SELECT
                            _row_idx, record_type, tx_id, src_tx, dst_tx,
                            time_step, label, features_json, ingested_at,
                            {batch_id}, current_timestamp()
                        FROM {source_ref.fqn}
                        WHERE _row_idx > {start_idx}
                        ORDER BY _row_idx
                        LIMIT {batch_size}
                    """,
                    warehouse_id=warehouse_id,
                )
                result = execute_sql(
                    statement=f"""
                        SELECT coalesce(max(_row_idx), {start_idx}) AS mx
                        FROM {bronze_ref.fqn}
                        WHERE playback_batch_id = {batch_id}
                    """,
                    warehouse_id=warehouse_id,
                )
                new_idx = scalar_int(result, "mx", start_idx)
                if new_idx <= start_idx:
                    upsert_state(
                        table_name=state_table,
                        warehouse_id=warehouse_id,
                        dataset_key=dataset_key,
                        is_playing=False,
                    )
                    break
                upsert_state(
                    table_name=state_table,
                    warehouse_id=warehouse_id,
                    dataset_key=dataset_key,
                    last_row_idx=new_idx,
                    is_playing=True,
                )
                if self._stop_event.wait(interval):
                    break
        except Exception:
            logger.exception("Playback loop failed")
            upsert_state(
                table_name=state_table,
                warehouse_id=warehouse_id,
                dataset_key=dataset_key,
                is_playing=False,
            )
        finally:
            upsert_state(
                table_name=state_table,
                warehouse_id=warehouse_id,
                dataset_key=dataset_key,
                is_playing=False,
            )


playback_controller = PlaybackController()


def flask_config_dict(app_config: Any) -> dict[str, Any]:
    """Normalize Flask config object into playback kwargs."""
    from bronze_injector.config import AppConfig, config_from_flask

    cfg = app_config if isinstance(app_config, AppConfig) else config_from_flask(app_config)
    key = cfg.dataset_key()
    cat, sch = cfg.BRONZE_INJECTOR_CATALOG, cfg.BRONZE_INJECTOR_SCHEMA
    return {
        "DATABRICKS_SQL_WAREHOUSE_ID": cfg.DATABRICKS_SQL_WAREHOUSE_ID,
        "dataset_key": key,
        "test_source_table": cfg.test_source_table(),
        "bronze_table": cfg.bronze_table(),
        "PLAYBACK_STATE_TABLE": cfg.PLAYBACK_STATE_TABLE,
        "DEMO_TABLES_REGISTRY_TABLE": cfg.DEMO_TABLES_REGISTRY_TABLE,
        "PLAYBACK_BATCH_SIZE": cfg.PLAYBACK_BATCH_SIZE,
        "PLAYBACK_INTERVAL_SEC": cfg.PLAYBACK_INTERVAL_SEC,
        "silver_table": f"{cat}.{sch}.silver_{key}",
        "gold_table": f"{cat}.{sch}.gold_{key}",
        "gold_graphlet_table": f"{cat}.{sch}.gold_graphlet_{key}",
    }
