"""Flask application factory for the bronze simulated injector Databricks App."""

from __future__ import annotations

import logging
import threading

from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from bronze_injector.config import AppConfig
from bronze_injector.routes.api import api_blueprint
from bronze_injector.services.dataset_loader import ensure_dataset_loaded
from bronze_injector.services.demo_tables_registry import register_dataset_tables
from bronze_injector.services.playback import flask_config_dict
from bronze_injector.services.playback_state import ensure_playback_state_table

logger = logging.getLogger(__name__)


def _startup_ensure_dataset(app: Flask) -> None:
    from bronze_injector.config import config_from_flask

    cfg = config_from_flask(app.config)
    if not cfg.AUTO_ENSURE_DATASET_ON_STARTUP:
        return
    warehouse_id = cfg.DATABRICKS_SQL_WAREHOUSE_ID
    if not warehouse_id:
        logger.warning("AUTO_ENSURE_DATASET_ON_STARTUP skipped: no warehouse id")
        return

    def _run() -> None:
        try:
            result = ensure_dataset_loaded(
                dataset_key=cfg.dataset_key(),
                source_table=cfg.test_source_table(),
                bronze_table=cfg.bronze_table(),
                catalog=cfg.BRONZE_INJECTOR_CATALOG,
                schema=cfg.BRONZE_INJECTOR_SCHEMA,
                volume_name=cfg.TEST_BRONZE_VOLUME_NAME,
                warehouse_id=warehouse_id,
            )
            pcfg = flask_config_dict(cfg)
            register_dataset_tables(
                registry_table=cfg.DEMO_TABLES_REGISTRY_TABLE,
                warehouse_id=warehouse_id,
                dataset_key=pcfg["dataset_key"],
                test_source_table=pcfg["test_source_table"],
                bronze_table=pcfg["bronze_table"],
                silver_table=pcfg["silver_table"],
                gold_table=pcfg["gold_table"],
                gold_graphlet_table=pcfg["gold_graphlet_table"],
            )
            ensure_playback_state_table(cfg.PLAYBACK_STATE_TABLE, warehouse_id)
            logger.info("Startup dataset ensure: %s", result)
        except Exception:
            logger.exception("Startup dataset ensure failed")

    threading.Thread(target=_run, name="startup-dataset-load", daemon=True).start()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(AppConfig())
    app.register_blueprint(api_blueprint, url_prefix="/api")
    _startup_ensure_dataset(app)

    @app.route("/")
    def index():
        from bronze_injector.config import config_from_flask

        cfg = config_from_flask(app.config)
        return jsonify(
            {
                "app": "arango-bronze-injector",
                "dataset": cfg.dataset_key(),
                "endpoints": {
                    "health": "/api/health",
                    "play": "POST /api/playback/play",
                    "stop": "POST /api/playback/stop",
                    "reset": "POST /api/playback/reset",
                    "status": "GET /api/playback/status",
                    "ensure_dataset": "POST /api/dataset/ensure-loaded",
                    "registry": "GET /api/registry/tables",
                },
            }
        )

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )
    return app
