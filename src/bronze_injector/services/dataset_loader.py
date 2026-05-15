"""Load configured test datasets into UC Delta (and optional volume staging)."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Iterator

import pandas as pd
import requests

from bronze_injector.services.databricks_sql import execute_sql, scalar_int
from bronze_injector.services.table_ref import parse_table_name

logger = logging.getLogger(__name__)

ELLIPTIC_BITCOIN_ZIP_URL = "https://data.pyg.org/datasets/EllipticBitcoinDataset.zip"

SOURCE_ROW_DDL = """
    _row_idx BIGINT,
    record_type STRING,
    tx_id STRING,
    src_tx STRING,
    dst_tx STRING,
    time_step INT,
    label INT,
    features_json STRING,
    ingested_at TIMESTAMP
"""


def ensure_uc_schema_volume(
    *,
    catalog: str,
    schema: str,
    volume_name: str,
    warehouse_id: str,
) -> None:
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume_name}`",
        warehouse_id=warehouse_id,
    )


def ensure_source_table(table_fqn: str, warehouse_id: str) -> None:
    ref = parse_table_name(table_fqn)
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{ref.catalog}`.`{ref.schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                {SOURCE_ROW_DDL}
            )
            USING DELTA
        """,
        warehouse_id=warehouse_id,
    )


def ensure_bronze_table(table_fqn: str, warehouse_id: str) -> None:
    ref = parse_table_name(table_fqn)
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                {SOURCE_ROW_DDL},
                playback_batch_id BIGINT,
                bronze_ingested_at TIMESTAMP
            )
            USING DELTA
        """,
        warehouse_id=warehouse_id,
    )


def source_row_count(table_fqn: str, warehouse_id: str) -> int:
    ref = parse_table_name(table_fqn)
    result = execute_sql(
        statement=f"SELECT count(*) AS cnt FROM {ref.fqn}",
        warehouse_id=warehouse_id,
    )
    return scalar_int(result, "cnt", 0)


def _download_elliptic_zip() -> bytes:
    logger.info("Downloading Elliptic Bitcoin dataset from %s", ELLIPTIC_BITCOIN_ZIP_URL)
    resp = requests.get(ELLIPTIC_BITCOIN_ZIP_URL, timeout=120)
    resp.raise_for_status()
    return resp.content


def _iter_elliptic_rows(zip_bytes: bytes) -> Iterator[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = {n.split("/")[-1]: n for n in zf.namelist()}
        feats_name = next((k for k in names if k.startswith("elliptic_txs_features")), None)
        edgelist_name = next((k for k in names if k.startswith("elliptic_txs_edgelist")), None)
        labels_name = next((k for k in names if k.startswith("elliptic_btc430_label")), None)
        if not feats_name or not edgelist_name:
            raise RuntimeError(f"Unexpected Elliptic zip layout: {list(names)[:20]}")

        labels: dict[str, int] = {}
        if labels_name:
            with zf.open(names[labels_name]) as f:
                label_df = pd.read_csv(f)
                if "txId" in label_df.columns and "class" in label_df.columns:
                    for _, row in label_df.iterrows():
                        labels[str(row["txId"])] = int(row["class"])

        row_idx = 0
        with zf.open(names[feats_name]) as f:
            tx_df = pd.read_csv(f)
            id_col = "txId" if "txId" in tx_df.columns else tx_df.columns[0]
            time_col = "time_step" if "time_step" in tx_df.columns else None
            feature_cols = [
                c
                for c in tx_df.columns
                if c not in (id_col, time_col, "class")
            ]
            for _, row in tx_df.iterrows():
                tx_id = str(row[id_col])
                feat = {c: row[c] for c in feature_cols}
                yield {
                    "_row_idx": row_idx,
                    "record_type": "node",
                    "tx_id": tx_id,
                    "src_tx": None,
                    "dst_tx": None,
                    "time_step": int(row[time_col]) if time_col and pd.notna(row[time_col]) else None,
                    "label": labels.get(tx_id),
                    "features_json": json.dumps(feat),
                }
                row_idx += 1

        with zf.open(names[edgelist_name]) as f:
            edge_df = pd.read_csv(f)
            cols = list(edge_df.columns)
            src_col = "txId1" if "txId1" in cols else cols[0]
            dst_col = "txId2" if "txId2" in cols else cols[1]
            for _, row in edge_df.iterrows():
                yield {
                    "_row_idx": row_idx,
                    "record_type": "edge",
                    "tx_id": None,
                    "src_tx": str(row[src_col]),
                    "dst_tx": str(row[dst_col]),
                    "time_step": None,
                    "label": None,
                    "features_json": None,
                }
                row_idx += 1


def _sql_literal(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def _insert_batch(table_fqn: str, rows: list[dict[str, Any]], warehouse_id: str) -> None:
    if not rows:
        return
    ref = parse_table_name(table_fqn)
    values_sql = []
    for r in rows:
        values_sql.append(
            "("
            + ", ".join(
                [
                    _sql_literal(r.get("_row_idx")),
                    _sql_literal(r.get("record_type")),
                    _sql_literal(r.get("tx_id")),
                    _sql_literal(r.get("src_tx")),
                    _sql_literal(r.get("dst_tx")),
                    _sql_literal(r.get("time_step")),
                    _sql_literal(r.get("label")),
                    _sql_literal(r.get("features_json")),
                    "current_timestamp()",
                ]
            )
            + ")"
        )
    execute_sql(
        statement=f"""
            INSERT INTO {ref.fqn}
            (_row_idx, record_type, tx_id, src_tx, dst_tx, time_step, label, features_json, ingested_at)
            VALUES {", ".join(values_sql)}
        """,
        warehouse_id=warehouse_id,
    )


def load_elliptic_bitcoin(
    *,
    source_table: str,
    warehouse_id: str,
    batch_size: int = 500,
) -> int:
    zip_bytes = _download_elliptic_zip()
    total = 0
    batch: list[dict[str, Any]] = []
    for row in _iter_elliptic_rows(zip_bytes):
        batch.append(row)
        if len(batch) >= batch_size:
            _insert_batch(source_table, batch, warehouse_id)
            total += len(batch)
            batch = []
    if batch:
        _insert_batch(source_table, batch, warehouse_id)
        total += len(batch)
    return total


def ensure_dataset_loaded(
    *,
    dataset_key: str,
    source_table: str,
    bronze_table: str,
    catalog: str,
    schema: str,
    volume_name: str,
    warehouse_id: str,
) -> dict[str, Any]:
    ensure_uc_schema_volume(
        catalog=catalog,
        schema=schema,
        volume_name=volume_name,
        warehouse_id=warehouse_id,
    )
    ensure_source_table(source_table, warehouse_id)
    ensure_bronze_table(bronze_table, warehouse_id)

    existing = source_row_count(source_table, warehouse_id)
    if existing > 0:
        return {
            "loaded": False,
            "reason": "already_present",
            "source_rows": existing,
            "source_table": source_table,
            "bronze_table": bronze_table,
        }

    key = (dataset_key or "elliptic_bitcoin").lower()
    if key in ("elliptic_bitcoin", "elliptic", "elliptic-bitcoin"):
        inserted = load_elliptic_bitcoin(
            source_table=source_table, warehouse_id=warehouse_id
        )
    else:
        raise ValueError(
            f"Unsupported dataset_key={dataset_key!r}. "
            "Supported: elliptic_bitcoin (PyG EllipticBitcoinDataset)."
        )

    return {
        "loaded": True,
        "source_rows": inserted,
        "source_table": source_table,
        "bronze_table": bronze_table,
    }
