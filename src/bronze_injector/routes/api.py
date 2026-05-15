"""Playback and dataset HTTP API for dashboard / automation."""

from __future__ import annotations

import logging
import threading

from flask import Blueprint, current_app, jsonify, request

from bronze_injector.config import config_from_flask
from bronze_injector.services.dataset_loader import ensure_dataset_loaded
from bronze_injector.services.demo_tables_registry import register_dataset_tables
from bronze_injector.services.injector_uc_registry import update_injector_registry_status
from bronze_injector.services.playback import flask_config_dict, playback_controller
from bronze_injector.services.playback_state import ensure_playback_state_table

logger = logging.getLogger(__name__)

api_blueprint = Blueprint("api", __name__)

_load_lock = threading.Lock()
_load_status: dict = {"status": "idle"}


def _cfg():
    return config_from_flask(current_app.config)


def _clamp_playback_interval_sec(raw: float) -> float:
    """Keep batch cadence within a safe range (dashboard-supplied values)."""
    return max(0.05, min(60.0, float(raw)))


def _playback_interval_sec_from_request(
    body: dict, config_default: float
) -> float:
    """Resolve interval from JSON body (per play) or env default."""
    if not body:
        return _clamp_playback_interval_sec(config_default)
    if "interval_sec" in body:
        return _clamp_playback_interval_sec(float(body["interval_sec"]))
    if "playback_hz" in body:
        hz = float(body["playback_hz"])
        if hz <= 0:
            raise ValueError("playback_hz must be positive")
        return _clamp_playback_interval_sec(1.0 / hz)
    return _clamp_playback_interval_sec(config_default)


def _playback_cfg() -> dict:
    return flask_config_dict(_cfg())


@api_blueprint.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_blueprint.get("/playback/status")
def playback_status():
    return jsonify(playback_controller.status_snapshot(_playback_cfg()))


@api_blueprint.post("/playback/play")
def playback_play():
    cfg_base = _playback_cfg()
    warehouse_id = cfg_base["DATABRICKS_SQL_WAREHOUSE_ID"]
    if not warehouse_id:
        return jsonify({"ok": False, "error": "DATABRICKS_SQL_WAREHOUSE_ID is not set"}), 503
    body = request.get_json(silent=True) or {}
    cfg = dict(cfg_base)
    try:
        cfg["PLAYBACK_INTERVAL_SEC"] = _playback_interval_sec_from_request(
            body,
            float(cfg.get("PLAYBACK_INTERVAL_SEC") or 1.0),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(playback_controller.play(cfg))


@api_blueprint.post("/playback/stop")
def playback_stop():
    return jsonify(playback_controller.stop(_playback_cfg()))


@api_blueprint.post("/playback/reset")
def playback_reset():
    return jsonify(playback_controller.reset(_playback_cfg()))


@api_blueprint.post("/dataset/ensure-loaded")
def dataset_ensure_loaded():
    app_cfg = _cfg()
    warehouse_id = app_cfg.DATABRICKS_SQL_WAREHOUSE_ID
    if not warehouse_id:
        return jsonify({"ok": False, "error": "DATABRICKS_SQL_WAREHOUSE_ID is not set"}), 503
    with _load_lock:
        try:
            import json

            result = ensure_dataset_loaded(
                dataset_key=app_cfg.dataset_key(),
                bronze_table=app_cfg.bronze_raw_data_table(),
                catalog=app_cfg.BRONZE_INJECTOR_CATALOG,
                schema=app_cfg.BRONZE_INJECTOR_SCHEMA,
                volume_name=app_cfg.TEST_BRONZE_VOLUME_NAME,
                warehouse_id=warehouse_id,
            )
            pcfg = _playback_cfg()
            register_dataset_tables(
                registry_table=app_cfg.DEMO_TABLES_REGISTRY_TABLE,
                warehouse_id=warehouse_id,
                dataset_key=pcfg["dataset_key"],
                bronze_table=pcfg["bronze_raw_data_table"],
                silver_table=pcfg["silver_table"],
                gold_table=pcfg["gold_table"],
                gold_graphlet_table=pcfg["gold_graphlet_table"],
            )
            ensure_playback_state_table(app_cfg.PLAYBACK_STATE_TABLE, warehouse_id)
            if result.get("loaded"):
                from bronze_injector.services.playback_state import upsert_state

                upsert_state(
                    table_name=app_cfg.PLAYBACK_STATE_TABLE,
                    warehouse_id=warehouse_id,
                    dataset_key=pcfg["dataset_key"],
                    last_row_idx=-1,
                    is_playing=False,
                    playback_file_marker=None,
                    update_playback_file_marker=True,
                )
            _load_status.update({"status": "ready", **result})
            update_injector_registry_status(
                current_app,
                status="READY",
                playback_status=None,
                status_detail=json.dumps(result, default=str),
            )
            return jsonify({"ok": True, **result})
        except Exception as exc:
            logger.exception("ensure_dataset_loaded failed")
            _load_status.update({"status": "error", "error": str(exc)})
            update_injector_registry_status(
                current_app,
                status="ERROR",
                playback_status="IDLE",
                status_detail=str(exc)[:4000],
            )
            return jsonify({"ok": False, "error": str(exc)}), 500


@api_blueprint.get("/dataset/load-status")
def dataset_load_status():
    return jsonify(_load_status)


@api_blueprint.get("/registry/tables")
def registry_tables():
    app_cfg = _cfg()
    warehouse_id = app_cfg.DATABRICKS_SQL_WAREHOUSE_ID
    if not warehouse_id:
        return jsonify({"ok": False, "error": "DATABRICKS_SQL_WAREHOUSE_ID is not set"}), 503
    from bronze_injector.services.databricks_sql import execute_sql
    from bronze_injector.services.table_ref import parse_table_name

    ref = parse_table_name(app_cfg.DEMO_TABLES_REGISTRY_TABLE)
    result = execute_sql(
        statement=f"""
            SELECT category, table_name, dataset_key, description, updated_at
            FROM {ref.fqn}
            ORDER BY dataset_key, category
        """,
        warehouse_id=warehouse_id,
    )
    return jsonify({"ok": True, **result})


@api_blueprint.get("/injector-registry/active")
def injector_registry_active_row():
    """Return the active UC row (same shape consumers get from SQL on the registry table)."""
    app_cfg = _cfg()
    warehouse_id = app_cfg.DATABRICKS_SQL_WAREHOUSE_ID
    if not warehouse_id:
        return jsonify({"ok": False, "error": "DATABRICKS_SQL_WAREHOUSE_ID is not set"}), 503
    from bronze_injector.services.databricks_sql import execute_sql
    from bronze_injector.services.table_ref import parse_table_name

    ref = parse_table_name(app_cfg.ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE)
    result = execute_sql(
        statement=f"""
            SELECT
                base_url,
                app_name,
                is_active,
                status,
                playback_status,
                dataset_key,
                status_detail,
                updated_at
            FROM {ref.fqn}
            WHERE is_active IS TRUE
            ORDER BY updated_at DESC
            LIMIT 1
        """,
        warehouse_id=warehouse_id,
    )
    rows = result.get("rows") or []
    return jsonify(
        {
            "ok": True,
            "row": rows[0] if rows else None,
            "columns": result.get("columns"),
        }
    )
