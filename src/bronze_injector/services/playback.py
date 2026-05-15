"""Background playback: ``data_uploader`` chunks → ``INSERT`` into ``bronze_raw_data``."""

from __future__ import annotations

import logging
import threading
from typing import Any

from bronze_injector.services.data_uploader import next_playback_chunk
from bronze_injector.services.databricks_sql import execute_sql, scalar_int
from bronze_injector.services.dataset_loader import ensure_bronze_raw_table, insert_bronze_playback_chunk
from bronze_injector.services.playback_state import get_state, max_row_idx_for_dataset, upsert_state
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)


class PlaybackController:
    """Single-process playback loop (use gunicorn --workers 1)."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._batch_id = 0
        self._flask_app: Any = None
        self._loop_interval_sec: float | None = None

    def attach_app(self, app: Any) -> None:
        self._flask_app = app

    def _uc_playback_idle(self, detail: str | None = None) -> None:
        app = self._flask_app
        if app is None:
            return
        try:
            from bronze_injector.services.injector_uc_registry import (
                update_injector_registry_status,
            )

            k: dict[str, Any] = {"playback_status": "IDLE"}
            if detail:
                k["status_detail"] = detail
            update_injector_registry_status(app, **k)
        except Exception:
            logger.debug("injector UC registry idle patch failed", exc_info=True)

    def _uc_playback_playing(self) -> None:
        app = self._flask_app
        if app is None:
            return
        try:
            from bronze_injector.services.injector_uc_registry import (
                update_injector_registry_status,
            )

            update_injector_registry_status(app, playback_status="PLAYING")
        except Exception:
            logger.debug("injector UC registry playing patch failed", exc_info=True)

    def _uc_playback_error(self, detail: str) -> None:
        app = self._flask_app
        if app is None:
            return
        try:
            from bronze_injector.services.injector_uc_registry import (
                update_injector_registry_status,
            )

            update_injector_registry_status(
                app,
                status="ERROR",
                playback_status="IDLE",
                status_detail=detail,
            )
        except Exception:
            logger.debug("injector UC registry error patch failed", exc_info=True)

    def status_snapshot(self, cfg: dict[str, Any]) -> dict[str, Any]:
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        dataset_key = cfg["dataset_key"]
        state_table = cfg["PLAYBACK_STATE_TABLE"]
        bronze_table = cfg["bronze_raw_data_table"]
        state = get_state(
            table_name=state_table,
            warehouse_id=warehouse_id,
            dataset_key=dataset_key,
        )
        bronze_max = max_row_idx_for_dataset(
            bronze_table=bronze_table, warehouse_id=warehouse_id, dataset_key=dataset_key
        )
        ref = parse_table_name(bronze_table)
        dk = (dataset_key or "").replace("'", "''")
        stale_n = scalar_int(
            execute_sql(
                statement=(
                    f"SELECT count(*) AS cnt FROM {ref.fqn} "
                    f"WHERE dataset_key = '{dk}' AND freshness = 'stale'"
                ),
                warehouse_id=warehouse_id,
            ),
            "cnt",
            0,
        )
        fresh_n = scalar_int(
            execute_sql(
                statement=(
                    f"SELECT count(*) AS cnt FROM {ref.fqn} "
                    f"WHERE dataset_key = '{dk}' AND freshness = 'fresh'"
                ),
                warehouse_id=warehouse_id,
            ),
            "cnt",
            0,
        )
        with self._lock:
            thread_alive = self._thread is not None and self._thread.is_alive()
        cfg_interval = float(cfg.get("PLAYBACK_INTERVAL_SEC") or 1.0)
        marker = state.get("playback_file_marker")
        return {
            "dataset_key": dataset_key,
            "is_playing": state["is_playing"] or thread_alive,
            "last_row_idx": state["last_row_idx"],
            "playback_file_marker": marker,
            "playback_interval_sec": (
                (
                    self._loop_interval_sec
                    if self._loop_interval_sec is not None
                    else cfg_interval
                )
                if thread_alive
                else cfg_interval
            ),
            "playback_interval_sec_config": cfg_interval,
            "last_row_idx_hint": (
                "highest _row_idx appended during playback (-1 = none yet); "
                "opaque chunk cursor in playback_file_marker"
            ),
            "bronze_max_row_idx": bronze_max,
            "bronze_stale_row_count": stale_n,
            "bronze_fresh_row_count": fresh_n,
            "bronze_raw_data_table": bronze_table,
            "volume_base_path": cfg.get("volume_base_path"),
            "thread_alive": thread_alive,
        }

    def play(self, cfg: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return {"ok": True, "message": "already_playing", **self.status_snapshot(cfg)}
            self._loop_interval_sec = float(cfg.get("PLAYBACK_INTERVAL_SEC") or 1.0)
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(dict(cfg),),
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
        self._uc_playback_playing()
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
        with self._lock:
            self._loop_interval_sec = None
        self._uc_playback_idle("stop_requested")
        return {"ok": True, "message": "stop_requested", **self.status_snapshot(cfg)}

    def reset(self, cfg: dict[str, Any]) -> dict[str, Any]:
        self.stop(cfg)
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        bronze_ref = parse_table_name(cfg["bronze_raw_data_table"])
        dk = (cfg["dataset_key"] or "").replace("'", "''")
        execute_sql(
            statement=f"DELETE FROM {bronze_ref.fqn} WHERE dataset_key = '{dk}'",
            warehouse_id=warehouse_id,
        )
        upsert_state(
            table_name=cfg["PLAYBACK_STATE_TABLE"],
            warehouse_id=warehouse_id,
            dataset_key=cfg["dataset_key"],
            last_row_idx=-1,
            is_playing=False,
            playback_file_marker=None,
            update_playback_file_marker=True,
        )
        self._uc_playback_idle("reset_complete")
        return {"ok": True, "message": "reset_complete", **self.status_snapshot(cfg)}

    def _run_loop(self, cfg: dict[str, Any]) -> None:
        warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
        dataset_key = cfg["dataset_key"]
        state_table = cfg["PLAYBACK_STATE_TABLE"]
        bronze_table = cfg["bronze_raw_data_table"]
        volume_base_path = cfg["volume_base_path"]
        batch_size = int(cfg.get("PLAYBACK_BATCH_SIZE") or 200)
        interval = float(cfg.get("PLAYBACK_INTERVAL_SEC") or 1.0)

        ensure_bronze_raw_table(bronze_table, warehouse_id)

        try:
            while not self._stop_event.is_set():
                state = get_state(
                    table_name=state_table,
                    warehouse_id=warehouse_id,
                    dataset_key=dataset_key,
                )
                last_row_idx = int(state["last_row_idx"])
                marker = state.get("playback_file_marker")
                marker_s = None if marker is None else str(marker)

                chunk = next_playback_chunk(
                    dataset_key=dataset_key,
                    volume_base_path=volume_base_path,
                    marker_json=marker_s,
                    batch_hint=batch_size,
                )

                if not chunk.rows:
                    if chunk.exhausted:
                        upsert_state(
                            table_name=state_table,
                            warehouse_id=warehouse_id,
                            dataset_key=dataset_key,
                            last_row_idx=last_row_idx,
                            is_playing=False,
                            playback_file_marker=chunk.next_marker,
                            update_playback_file_marker=True,
                        )
                        self._uc_playback_idle("data_uploader_exhausted")
                        break
                    logger.warning(
                        "data_uploader returned no rows but not exhausted (dataset=%s)",
                        dataset_key,
                    )
                    upsert_state(
                        table_name=state_table,
                        warehouse_id=warehouse_id,
                        dataset_key=dataset_key,
                        is_playing=False,
                        playback_file_marker=marker_s,
                        update_playback_file_marker=True,
                    )
                    self._uc_playback_idle("data_uploader_empty_chunk")
                    break

                self._batch_id += 1
                batch_id = self._batch_id
                start_idx = last_row_idx + 1
                normalized: list[dict[str, Any]] = []
                for i, r in enumerate(chunk.rows):
                    row = dict(r)
                    row["_row_idx"] = start_idx + i
                    normalized.append(row)

                insert_bronze_playback_chunk(
                    table_fqn=bronze_table,
                    dataset_key=dataset_key,
                    rows=normalized,
                    warehouse_id=warehouse_id,
                    freshness="fresh",
                    playback_batch_id=batch_id,
                )
                new_last = start_idx + len(normalized) - 1
                upsert_state(
                    table_name=state_table,
                    warehouse_id=warehouse_id,
                    dataset_key=dataset_key,
                    last_row_idx=new_last,
                    is_playing=(not chunk.exhausted),
                    playback_file_marker=chunk.next_marker,
                    update_playback_file_marker=True,
                )

                if chunk.exhausted:
                    self._uc_playback_idle("playback_stream_complete")
                    break

                if self._stop_event.wait(interval):
                    break
        except Exception:
            logger.exception("Playback loop failed")
            self._uc_playback_error("playback_exception")
            upsert_state(
                table_name=state_table,
                warehouse_id=warehouse_id,
                dataset_key=dataset_key,
                is_playing=False,
            )
        finally:
            with self._lock:
                self._loop_interval_sec = None
            upsert_state(
                table_name=state_table,
                warehouse_id=warehouse_id,
                dataset_key=dataset_key,
                is_playing=False,
            )
            self._uc_playback_idle(None)


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
        "bronze_raw_data_table": cfg.bronze_raw_data_table(),
        "volume_base_path": cfg.test_volume_path(),
        "PLAYBACK_STATE_TABLE": cfg.PLAYBACK_STATE_TABLE,
        "DEMO_TABLES_REGISTRY_TABLE": cfg.DEMO_TABLES_REGISTRY_TABLE,
        "PLAYBACK_BATCH_SIZE": cfg.PLAYBACK_BATCH_SIZE,
        "PLAYBACK_INTERVAL_SEC": cfg.PLAYBACK_INTERVAL_SEC,
        "silver_table": f"{cat}.{sch}.silver_{key}",
        "gold_table": f"{cat}.{sch}.gold_{key}",
        "gold_graphlet_table": f"{cat}.{sch}.gold_graphlet_{key}",
    }
