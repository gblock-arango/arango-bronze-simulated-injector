"""Bootstrap datasets into a UC volume (download / unzip); ensure empty ``bronze_raw_data`` schema."""

from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from typing import Any

import requests

from bronze_injector.services.databricks_sql import execute_sql, scalar_int
from bronze_injector.services.table_ref import TableRef, parse_table_name

logger = logging.getLogger(__name__)

# Mirrors ``torch_geometric.datasets.EllipticBitcoinDataset.download()`` — three CSV archives,
# not the deprecated single ``EllipticBitcoinDataset.zip`` (often returns HTTP 403).
ELLIPTIC_PYG_BASE_DEFAULT = "https://data.pyg.org/datasets/elliptic"
ELLIPTIC_PYG_ARCHIVE_NAMES = (
    "elliptic_txs_features.csv.zip",
    "elliptic_txs_edgelist.csv.zip",
    "elliptic_txs_classes.csv.zip",
)

_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/zip,application/octet-stream,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://data.pyg.org/",
}

BOOTSTRAP_MANIFEST_NAME = ".arango_bronze_injector_bootstrap.json"

BRONZE_RAW_ROW_DDL = """
    _row_idx BIGINT,
    dataset_key STRING NOT NULL,
    freshness STRING NOT NULL,
    record_type STRING,
    tx_id STRING,
    src_tx STRING,
    dst_tx STRING,
    time_step INT,
    label INT,
    features_json STRING,
    ingested_at TIMESTAMP,
    playback_batch_id BIGINT,
    bronze_refreshed_at TIMESTAMP
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


def ensure_bronze_raw_table(table_fqn: str, warehouse_id: str) -> None:
    ref = parse_table_name(table_fqn)
    execute_sql(
        statement=f"CREATE SCHEMA IF NOT EXISTS `{ref.catalog}`.`{ref.schema}`",
        warehouse_id=warehouse_id,
    )
    execute_sql(
        statement=f"""
            CREATE TABLE IF NOT EXISTS {ref.fqn} (
                {BRONZE_RAW_ROW_DDL}
            )
            USING DELTA
        """,
        warehouse_id=warehouse_id,
    )
    _try_grant_select_modify_account_users(ref, warehouse_id)


def _try_grant_select_modify_account_users(ref: TableRef, warehouse_id: str) -> None:
    try:
        execute_sql(
            statement=f"GRANT SELECT, MODIFY ON TABLE {ref.fqn} TO `account users`",
            warehouse_id=warehouse_id,
        )
    except Exception as exc:
        logger.info(
            "Could not GRANT %s to `account users`: %s",
            ref.fqn,
            exc,
        )


def bronze_row_count_for_dataset(
    table_fqn: str, warehouse_id: str, dataset_key: str
) -> int:
    ref = parse_table_name(table_fqn)
    dk = (dataset_key or "").replace("'", "''")
    result = execute_sql(
        statement=(
            f"SELECT count(*) AS cnt FROM {ref.fqn} WHERE dataset_key = '{dk}'"
        ),
        warehouse_id=warehouse_id,
    )
    return scalar_int(result, "cnt", 0)


def volume_base_os_path(*, catalog: str, schema: str, volume_name: str) -> str:
    return f"/Volumes/{catalog}/{schema}/{volume_name}"


def _read_bootstrap_manifest(volume_base: str) -> dict[str, Any] | None:
    path = os.path.join(volume_base, BOOTSTRAP_MANIFEST_NAME)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return None


def _write_bootstrap_manifest(volume_base: str, payload: dict[str, Any]) -> None:
    os.makedirs(volume_base, exist_ok=True)
    path = os.path.join(volume_base, BOOTSTRAP_MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def safe_extract_zip(zip_bytes: bytes, dest_dir: str) -> None:
    """Extract zip under ``dest_dir`` with basic zip-slip checks."""
    os.makedirs(dest_dir, exist_ok=True)
    abs_dest = os.path.abspath(dest_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or name.startswith("..") or "/../" in name:
                raise RuntimeError(f"Unsafe zip entry: {name!r}")
            target = os.path.normpath(os.path.join(dest_dir, name))
            abs_target = os.path.abspath(target)
            rel = os.path.relpath(abs_target, abs_dest)
            if rel.startswith("..") or rel == "..":
                raise RuntimeError(f"Zip slip blocked: {name!r}")
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())


def _download_http_bytes(url: str, *, timeout: int = 300) -> bytes:
    """Fetch bytes from ``url`` using browser-like headers (reduces CDN/WAF 403s)."""
    logger.info("Downloading %s", url)
    resp = requests.get(
        url,
        timeout=timeout,
        headers=_DOWNLOAD_HEADERS,
        allow_redirects=True,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        body_preview = (resp.text[:500] if getattr(resp, "text", None) else "") or ""
        logger.error(
            "HTTP download failed url=%s status=%s preview=%r",
            url,
            resp.status_code,
            body_preview,
        )
        raise
    return resp.content


def bootstrap_elliptic_bitcoin_volume(*, volume_base: str, dataset_key_norm: str) -> dict[str, Any]:
    """Stage Elliptic files under ``volume_base``: PyG-style three zips, or one zip if overridden."""
    monolithic = (os.environ.get("ELLIPTIC_BITCOIN_ZIP_URL") or "").strip()
    source_urls: list[str]

    if monolithic:
        zip_bytes = _download_http_bytes(monolithic)
        safe_extract_zip(zip_bytes, volume_base)
        source_urls = [monolithic]
    else:
        base = (
            os.environ.get("ELLIPTIC_DATASET_BASE_URL") or ELLIPTIC_PYG_BASE_DEFAULT
        ).strip().rstrip("/")
        source_urls = []
        for archive_name in ELLIPTIC_PYG_ARCHIVE_NAMES:
            url = f"{base}/{archive_name}"
            source_urls.append(url)
            safe_extract_zip(_download_http_bytes(url), volume_base)

    manifest = {
        "dataset_key": dataset_key_norm.lower().replace("-", "_"),
        "kind": "elliptic_bitcoin",
        "source_urls": source_urls,
    }
    _write_bootstrap_manifest(volume_base, manifest)
    return manifest


def insert_bronze_playback_chunk(
    *,
    table_fqn: str,
    dataset_key: str,
    rows: list[dict[str, Any]],
    warehouse_id: str,
    freshness: str,
    playback_batch_id: int,
) -> None:
    """Insert rows produced during playback (typically ``freshness='fresh'``)."""
    if not rows:
        return

    def _sql_literal(val: Any) -> str:
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        s = str(val).replace("'", "''")
        return f"'{s}'"

    ref = parse_table_name(table_fqn)
    dk = (dataset_key or "").replace("'", "''")
    fresh_esc = (freshness or "fresh").replace("'", "''")
    values_sql = []
    for r in rows:
        values_sql.append(
            "("
            + ", ".join(
                [
                    _sql_literal(r.get("_row_idx")),
                    f"'{dk}'",
                    f"'{fresh_esc}'",
                    _sql_literal(r.get("record_type")),
                    _sql_literal(r.get("tx_id")),
                    _sql_literal(r.get("src_tx")),
                    _sql_literal(r.get("dst_tx")),
                    _sql_literal(r.get("time_step")),
                    _sql_literal(r.get("label")),
                    _sql_literal(r.get("features_json")),
                    "current_timestamp()",
                    str(int(playback_batch_id)),
                    "current_timestamp()",
                ]
            )
            + ")"
        )
    execute_sql(
        statement=f"""
            INSERT INTO {ref.fqn}
            (_row_idx, dataset_key, freshness, record_type, tx_id, src_tx, dst_tx,
             time_step, label, features_json, ingested_at, playback_batch_id, bronze_refreshed_at)
            VALUES {", ".join(values_sql)}
        """,
        warehouse_id=warehouse_id,
    )


def ensure_dataset_loaded(
    *,
    dataset_key: str,
    bronze_table: str,
    catalog: str,
    schema: str,
    volume_name: str,
    warehouse_id: str,
) -> dict[str, Any]:
    """Create volume + empty bronze table; download/unzip dataset files into the volume once."""
    ensure_uc_schema_volume(
        catalog=catalog,
        schema=schema,
        volume_name=volume_name,
        warehouse_id=warehouse_id,
    )
    ensure_bronze_raw_table(bronze_table, warehouse_id)

    volume_base = volume_base_os_path(
        catalog=catalog, schema=schema, volume_name=volume_name
    )
    key_lower = (dataset_key or "elliptic_bitcoin").lower().replace("-", "_")

    manifest = _read_bootstrap_manifest(volume_base)
    man_key = (
        str(manifest.get("dataset_key", "")).lower().replace("-", "_")
        if manifest
        else ""
    )
    if manifest and man_key == key_lower:
        return {
            "loaded": False,
            "reason": "already_staged",
            "bootstrap_manifest": manifest,
            "volume_path": volume_base,
            "bronze_table": bronze_table,
            "dataset_key": dataset_key,
            "bronze_rows_for_dataset": bronze_row_count_for_dataset(
                bronze_table, warehouse_id, key_lower
            ),
        }

    if key_lower in ("elliptic_bitcoin", "elliptic"):
        try:
            manifest = bootstrap_elliptic_bitcoin_volume(
                volume_base=volume_base,
                dataset_key_norm=key_lower,
            )
        except OSError as exc:
            logger.warning("Volume filesystem write failed (%s); retry may succeed", exc)
            raise
    else:
        raise ValueError(
            f"Unsupported dataset_key={dataset_key!r}. "
            "Supported: elliptic_bitcoin (PyG EllipticBitcoinDataset)."
        )

    return {
        "loaded": True,
        "bootstrap": "volume_extract",
        "bootstrap_manifest": manifest,
        "volume_path": volume_base,
        "bronze_table": bronze_table,
        "dataset_key": dataset_key,
        "bronze_rows_for_dataset": bronze_row_count_for_dataset(
            bronze_table, warehouse_id, key_lower
        ),
    }
