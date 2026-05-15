# arango-bronze-simulated-injector

Databricks App that **bootstrap-downloads** a dataset into a UC **volume** (zip → extracted files), keeps **`bronze_raw_data`** empty at bootstrap, then **PLAY** streams rows via a per-dataset **`data_uploader`** into **`bronze_raw_data`** (`INSERT`, **`freshness=fresh`**). Intended for demos with medallion pipelines and the Arango dashboard.

Default dataset: [PyG `EllipticBitcoinDataset`](https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html) (~203k nodes + ~234k edges). Bootstrap mirrors upstream PyG: **three** archives under `https://data.pyg.org/datasets/elliptic/` (`elliptic_txs_features.csv.zip`, `elliptic_txs_edgelist.csv.zip`, `elliptic_txs_classes.csv.zip`). The legacy single-file `EllipticBitcoinDataset.zip` URL often returns **403** — do not use it unless you mirror it yourself (see **`ELLIPTIC_BITCOIN_ZIP_URL`**). HTTP downloads send browser-like `User-Agent` and `Referer` to reduce CDN blocks.

## Layout

Matches sibling apps (`arango-dashboard-app`):

| File | Purpose |
|------|---------|
| `app.yaml` | Gunicorn command, env, SQL warehouse resource |
| `deploy_app.sh` | `databricks sync` + `apps deploy` + UC grants |
| `databricks.yml` | Standalone bundle (optional) |
| `resources/bronze_injector.app.yml` | App resource for solo bundle deploy |
| `src/bronze_injector/` | Flask app + playback services |
| `src/bronze_injector/services/data_uploader.py` | Per-dataset chunk producers (**stub** until implemented) |
| `src/wsgi.py` | Gunicorn entry (`PYTHONPATH=src`) |

## Unity Catalog objects

| Object | Default name |
|--------|----------------|
| Volume | `workspace.default.test_bronze_data` → `/Volumes/workspace/default/test_bronze_data` — **extracted dataset files +** `.arango_bronze_injector_bootstrap.json` manifest |
| Bronze table (single) | `workspace.default.bronze_raw_data` — created empty at bootstrap; playback **INSERT**s with **`dataset_key`**, **`freshness`**, payload columns, **`_row_idx`**, **`playback_batch_id`**, **`bronze_refreshed_at`** |
| Playback state | `workspace.default.arango_bronze_simulated_injector_playback_state` — **`last_row_idx`** (last appended **`_row_idx`**), **`playback_file_marker`** (opaque JSON/string cursor for **`data_uploader`**), **`is_playing`** |
| Demo registry | `workspace.default.demo_tables_registry` |
| Injector URL registry | `workspace.default.arango_bronze_simulated_injector_registry` |

**Bootstrap:** Ensures schema/volume and **`bronze_raw_data`** DDL. If the volume manifest is absent, downloads the PyG CSV archives (or one zip if **`ELLIPTIC_BITCOIN_ZIP_URL`** is set), **unzips into the volume** (zip-slip safe), writes **`.arango_bronze_injector_bootstrap.json`** with **`source_urls`**. **No bronze rows** are inserted during bootstrap.

**Playback:** Each tick calls **`next_playback_chunk`** in `data_uploader.py` with **`volume_base_path`** and **`playback_file_marker`**. Returned rows are **`INSERT`**ed as **`fresh`** with monotonic **`_row_idx`**. The UC playback row stores **`playback_file_marker`** returned by the uploader (`NULL` when cleared).

**`data_uploader` stub:** **`elliptic_bitcoin`** / **`elliptic`** are registered to a stub that returns **`exhausted`** immediately with **no rows**, so PLAY stops until you implement a real uploader (`register_dataset_uploader(...)`).

**RESET:** Stops playback, **`DELETE`**s all **`bronze_raw_data`** rows for the **`dataset_key`**, sets **`last_row_idx=-1`**, clears **`playback_file_marker`**. Volume files are **not** deleted.

**Migration:** Older flows bulk-loaded **`stale`** rows at bootstrap. With this version, clear bronze (RESET) and remove the volume manifest / re-bootstrap if you need the new staging layout.

### Injector URL registry (like `arango_agent_registry`)

The app **MERGE**s its public **`base_url`** (`https://….databricksapps.com`, no trailing slash) into  
**`arango_bronze_simulated_injector_registry`** together with **`status`**, **`playback_status`**, **`dataset_key`**, and **`status_detail`**, so consumers can read the same details you would otherwise put in **`BRONZE_INJECTOR_BASE_URL`**.

| Column | Typical values |
|--------|----------------|
| `status` | `STARTING` → `READY` / `ERROR` (dataset load lifecycle) |
| `playback_status` | `IDLE` / `PLAYING` |
| `status_detail` | JSON summary of last load or a short error marker |

Env: **`ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE`**, **`ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_AUTO_CREATE`**.  
Post-deploy: **`./update_arango_bronze_simulated_injector_registry_uc.sh`** (wired from **`deploy_app.sh`**).

The **arango-dashboard-app** resolves the injector base URL from UC (or **`BRONZE_INJECTOR_BASE_URL`**) and surfaces the active row under **`GET /api/debug/startup-status`** (`bronze_injector_*` keys).

Registry rows (for jobs/pipelines):

- `category=bronze` → bronze table FQN  
- `category=silver` → `workspace.default.silver_<dataset>` (placeholder until pipeline creates it)  
- `category=gold` / `gold-graphlet` → same pattern  

Pipelines can `SELECT table_name FROM workspace.default.demo_tables_registry WHERE category = 'bronze' AND dataset_key = 'elliptic_bitcoin'`.

## HTTP API (dashboard / curl)

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/api/playback/play` | Start playback loop; optional JSON **`{"interval_sec":1}`** or **`{"playback_hz":1}`** (clamped 0.05–60 s); default **`PLAYBACK_INTERVAL_SEC`** (**1** s) |
| `POST` | `/api/playback/stop` | Stop playback loop |
| `POST` | `/api/playback/reset` | **`DELETE`** bronze rows for dataset; reset **`last_row_idx`** / **`playback_file_marker`** |
| `GET` | `/api/playback/status` | **`playback_file_marker`**, **`last_row_idx`**, counts, interval hints |
| `POST` | `/api/dataset/ensure-loaded` | Bootstrap volume (download/unzip) if manifest missing; ensure empty bronze DDL |
| `GET` | `/api/registry/tables` | List `demo_tables_registry` |
| `GET` | `/api/injector-registry/active` | Active UC row (base_url, status, playback_status, …) |

Example (after deploy):

```bash
export INJECTOR_URL="https://....databricksapps.com"
curl -sS -X POST "${INJECTOR_URL}/api/playback/play" \
  -H 'Content-Type: application/json' \
  -d '{"playback_hz":1}'
curl -sS -X POST "${INJECTOR_URL}/api/playback/stop"
curl -sS -X POST "${INJECTOR_URL}/api/playback/reset"
```

Wire the dashboard to these endpoints (same auth model as other app-to-app calls: user token or service principal with `CAN_USE` on this app).

## Configuration (`app.yaml` / bundle)

| Env | Default | Meaning |
|-----|---------|---------|
| `DATABRICKS_SQL_WAREHOUSE_ID` | (required) | SQL warehouse for DDL/DML |
| `BRONZE_INJECTOR_DATASET` | `elliptic_bitcoin` | Dataset key (column `dataset_key` + registry suffixes) |
| `BRONZE_RAW_DATA_TABLE` | `workspace.default.bronze_raw_data` | Single bronze Delta table |
| `TEST_BRONZE_VOLUME_NAME` | `test_bronze_data` | UC volume name |
| `DEMO_TABLES_REGISTRY_TABLE` | `workspace.default.demo_tables_registry` | Medallion name registry |
| `PLAYBACK_BATCH_SIZE` | `200` | Hint passed to **`data_uploader`** (`batch_hint`) |
| `PLAYBACK_INTERVAL_SEC` | `1` | Seconds between chunks (~1 Hz); override **`POST /api/playback/play`** JSON |
| `AUTO_ENSURE_DATASET_ON_STARTUP` | `true` | Background **volume bootstrap** on boot (not bronze inserts) |
| `ELLIPTIC_DATASET_BASE_URL` | `https://data.pyg.org/datasets/elliptic` | Override base URL for the three **`*.csv.zip`** archives |
| `ELLIPTIC_BITCOIN_ZIP_URL` | *(unset)* | If set, download **this single zip** only (internal mirror), instead of the three-archive PyG layout |

## Deploy

**Solo:**

```bash
export DATABRICKS_SQL_WAREHOUSE_ID=<warehouse-hex>
./deploy_app.sh
```

**Platform bundle** (`arango-platform-bundle`): symlink `apps/arango-bronze-simulated-injector` → this repo; `databricks bundle deploy -t dev` deploys with gateway, agent, and dashboard.

**Human visibility (`account users`):** `./deploy_app.sh` **pre-creates** schemas, volume, and Delta tables (owner = your deploying identity where allowed) then runs tolerant **`GRANT SELECT, MODIFY ON TABLE … TO \`account users\``** and **`READ VOLUME`** on the staging volume—the same pattern as **arango-gateway-app**, so UC browser and notebooks can inspect data, not only the app service principal.

If **`account users`** is disabled in your metastore policy, grants may log NOTES; rely on metastore admins or workspace-specific grants.

App name: `arango-bronze-injector` (≤26 chars). Bundle target suffix: `arango-bronze-injector-dev`.

**Note:** Gunicorn runs with `--workers 1` so a single in-process playback thread is authoritative.

## First bootstrap

On startup (or `POST /api/dataset/ensure-loaded`), if **`${volume}/.arango_bronze_injector_bootstrap.json`** is absent for the configured **`dataset_key`**, the app downloads the three Elliptic **`*.csv.zip`** files (PyG layout), extracts CSVs into **`/Volumes/<catalog>/<schema>/<volume>/`**, unless **`ELLIPTIC_BITCOIN_ZIP_URL`** points at one bundled zip. **`bronze_raw_data`** stays empty until PLAY. To force re-bootstrap, remove the manifest (and extracted tree) from the volume and call **`ensure-loaded`** again.
