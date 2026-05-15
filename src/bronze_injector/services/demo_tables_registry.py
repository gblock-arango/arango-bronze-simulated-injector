"""Unity Catalog registry of demo medallion table names (bronze / silver / gold / gold-graphlet)."""

from __future__ import annotations

import logging

from bronze_injector.services.databricks_sql import execute_sql
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)

VALID_CATEGORIES = frozenset({"bronze", "silver", "gold", "gold-graphlet"})


def ensure_demo_tables_registry(table_name: str, warehouse_id: str) -> None:
    ref = parse_table_name(table_name)
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{ref.catalog}`.`{ref.schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                category STRING NOT NULL,
                table_name STRING NOT NULL,
                dataset_key STRING,
                description STRING,
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
        logger.info("Could not grant demo_tables_registry to account users: %s", exc)


def upsert_registry_row(
    *,
    registry_table: str,
    warehouse_id: str,
    category: str,
    table_fqn: str,
    dataset_key: str,
    description: str = "",
) -> None:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid registry category: {category}")
    ref = parse_table_name(registry_table)
    safe_cat = category.replace("'", "''")
    safe_tbl = table_fqn.replace("'", "''")
    safe_key = (dataset_key or "").replace("'", "''")
    safe_desc = (description or "").replace("'", "''")
    execute_sql(
        statement=f"""
            MERGE INTO {ref.fqn} t
            USING (
                SELECT
                    '{safe_cat}' AS category,
                    '{safe_tbl}' AS table_name,
                    '{safe_key}' AS dataset_key,
                    '{safe_desc}' AS description,
                    current_timestamp() AS updated_at
            ) s
            ON t.category = s.category AND t.dataset_key = s.dataset_key
            WHEN MATCHED THEN UPDATE SET
                table_name = s.table_name,
                description = s.description,
                updated_at = s.updated_at
            WHEN NOT MATCHED THEN INSERT *
        """,
        warehouse_id=warehouse_id,
    )


def register_dataset_tables(
    *,
    registry_table: str,
    warehouse_id: str,
    dataset_key: str,
    bronze_table: str,
    silver_table: str = "",
    gold_table: str = "",
    gold_graphlet_table: str = "",
) -> None:
    ensure_demo_tables_registry(registry_table, warehouse_id)
    upsert_registry_row(
        registry_table=registry_table,
        warehouse_id=warehouse_id,
        category="bronze",
        table_fqn=bronze_table,
        dataset_key=dataset_key,
        description="bronze_raw_data: stale→fresh simulated time (single table)",
    )
    if silver_table:
        upsert_registry_row(
            registry_table=registry_table,
            warehouse_id=warehouse_id,
            category="silver",
            table_fqn=silver_table,
            dataset_key=dataset_key,
            description="Silver layer (populated by medallion pipeline)",
        )
    if gold_table:
        upsert_registry_row(
            registry_table=registry_table,
            warehouse_id=warehouse_id,
            category="gold",
            table_fqn=gold_table,
            dataset_key=dataset_key,
            description="Gold layer (populated by medallion pipeline)",
        )
    if gold_graphlet_table:
        upsert_registry_row(
            registry_table=registry_table,
            warehouse_id=warehouse_id,
            category="gold-graphlet",
            table_fqn=gold_graphlet_table,
            dataset_key=dataset_key,
            description="Gold graphlet layer",
        )
