"""Playback and dataset HTTP API for dashboard / automation."""

from __future__ import annotations

import logging
import threading

from flask import Blueprint, current_app, jsonify

from bronze_injector.config import config_from_flask
from bronze_injector.services.dataset_loader import ensure_dataset_loaded
from bronze_injector.services.demo_tables_registry import register_dataset_tables
from bronze_injector.services.playback import flask_config_dict, playback_controller
from bronze_injector.services.playback_state import ensure_playback_state_table

logger = logging.getLogger(__name__)

api_blueprint = Blueprint("api", __name__)

_load_lock = threading.Lock()
_load_status: dict = {"status": "idle"}


def _cfg():
    return config_from_flask(current_app.config)


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
    cfg = _playback_cfg()
    warehouse_id = cfg["DATABRICKS_SQL_WAREHOUSE_ID"]
    if not warehouse_id:
        return jsonify({"ok": False, "error": "DATABRICKS_SQL_WAREHOUSE_ID is not set"}), 503
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
            result = ensure_dataset_loaded(
                dataset_key=app_cfg.dataset_key(),
                source_table=app_cfg.test_source_table(),
                bronze_table=app_cfg.bronze_table(),
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
                test_source_table=pcfg["test_source_table"],
                bronze_table=pcfg["bronze_table"],
                silver_table=pcfg["silver_table"],
                gold_table=pcfg["gold_table"],
                gold_graphlet_table=pcfg["gold_graphlet_table"],
            )
            ensure_playback_state_table(app_cfg.PLAYBACK_STATE_TABLE, warehouse_id)
            _load_status.update({"status": "ready", **result})
            return jsonify({"ok": True, **result})
        except Exception as exc:
            logger.exception("ensure_dataset_loaded failed")
            _load_status.update({"status": "error", "error": str(exc)})
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
