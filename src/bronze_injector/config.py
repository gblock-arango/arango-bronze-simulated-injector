"""Runtime configuration for the bronze injector Databricks App."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name, default) or "").strip()


def _env_bool(name: str, default: bool = False) -> bool:
    return _env(name, "true" if default else "false").lower() in ("1", "true", "yes")


@dataclass
class AppConfig:
    DATABRICKS_SQL_WAREHOUSE_ID: str = field(
        default_factory=lambda: _env("DATABRICKS_SQL_WAREHOUSE_ID")
    )
    BRONZE_INJECTOR_CATALOG: str = field(
        default_factory=lambda: _env("BRONZE_INJECTOR_CATALOG", "workspace")
    )
    BRONZE_INJECTOR_SCHEMA: str = field(
        default_factory=lambda: _env("BRONZE_INJECTOR_SCHEMA", "default")
    )
    BRONZE_INJECTOR_DATASET: str = field(
        default_factory=lambda: _env("BRONZE_INJECTOR_DATASET", "elliptic_bitcoin")
    )
    TEST_BRONZE_VOLUME_NAME: str = field(
        default_factory=lambda: _env("TEST_BRONZE_VOLUME_NAME", "test_bronze_data")
    )
    DEMO_TABLES_REGISTRY_TABLE: str = field(
        default_factory=lambda: _env(
            "DEMO_TABLES_REGISTRY_TABLE", "workspace.default.demo_tables_registry"
        )
    )
    PLAYBACK_STATE_TABLE: str = field(
        default_factory=lambda: _env(
            "PLAYBACK_STATE_TABLE", "workspace.default.bronze_injector_playback_state"
        )
    )
    PLAYBACK_BATCH_SIZE: int = field(
        default_factory=lambda: int(_env("PLAYBACK_BATCH_SIZE", "200") or "200")
    )
    PLAYBACK_INTERVAL_SEC: float = field(
        default_factory=lambda: float(_env("PLAYBACK_INTERVAL_SEC", "0.25") or "0.25")
    )
    AUTO_ENSURE_DATASET_ON_STARTUP: bool = field(
        default_factory=lambda: _env_bool("AUTO_ENSURE_DATASET_ON_STARTUP", True)
    )

    def dataset_key(self) -> str:
        return (self.BRONZE_INJECTOR_DATASET or "elliptic_bitcoin").replace("-", "_")

    def test_source_table(self) -> str:
        key = self.dataset_key()
        return f"{self.BRONZE_INJECTOR_CATALOG}.{self.BRONZE_INJECTOR_SCHEMA}.test_bronze_data_{key}"

    def bronze_table(self) -> str:
        key = self.dataset_key()
        return f"{self.BRONZE_INJECTOR_CATALOG}.{self.BRONZE_INJECTOR_SCHEMA}.bronze_{key}"

    def test_volume_path(self) -> str:
        return (
            f"/Volumes/{self.BRONZE_INJECTOR_CATALOG}/{self.BRONZE_INJECTOR_SCHEMA}/"
            f"{self.TEST_BRONZE_VOLUME_NAME}"
        )


def config_from_flask(flask_config: object) -> AppConfig:
    """Build AppConfig from Flask ``app.config`` (dict-like)."""
    if isinstance(flask_config, AppConfig):
        return flask_config
    get = getattr(flask_config, "get", None)
    if get is None:
        get = lambda k, d="": getattr(flask_config, k, d)  # type: ignore[misc]
    return AppConfig(
        DATABRICKS_SQL_WAREHOUSE_ID=str(get("DATABRICKS_SQL_WAREHOUSE_ID", "") or ""),
        BRONZE_INJECTOR_CATALOG=str(get("BRONZE_INJECTOR_CATALOG", "workspace") or "workspace"),
        BRONZE_INJECTOR_SCHEMA=str(get("BRONZE_INJECTOR_SCHEMA", "default") or "default"),
        BRONZE_INJECTOR_DATASET=str(get("BRONZE_INJECTOR_DATASET", "elliptic_bitcoin") or "elliptic_bitcoin"),
        TEST_BRONZE_VOLUME_NAME=str(get("TEST_BRONZE_VOLUME_NAME", "test_bronze_data") or "test_bronze_data"),
        DEMO_TABLES_REGISTRY_TABLE=str(
            get("DEMO_TABLES_REGISTRY_TABLE", "workspace.default.demo_tables_registry")
            or "workspace.default.demo_tables_registry"
        ),
        PLAYBACK_STATE_TABLE=str(
            get("PLAYBACK_STATE_TABLE", "workspace.default.bronze_injector_playback_state")
            or "workspace.default.bronze_injector_playback_state"
        ),
        PLAYBACK_BATCH_SIZE=int(get("PLAYBACK_BATCH_SIZE", 200) or 200),
        PLAYBACK_INTERVAL_SEC=float(get("PLAYBACK_INTERVAL_SEC", 0.25) or 0.25),
        AUTO_ENSURE_DATASET_ON_STARTUP=str(
            get("AUTO_ENSURE_DATASET_ON_STARTUP", "true")
        ).lower()
        in ("1", "true", "yes"),
    )
