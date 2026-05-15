# arango-bronze-simulated-injector

Databricks App that loads a **frozen test dataset** into Unity Catalog and **replays** rows into a **bronze** Delta table on demand (PLAY / STOP / RESET). Intended for demos with medallion pipelines and the Arango dashboard.

Default dataset: [PyG `EllipticBitcoinDataset`](https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html) (~203k nodes + ~234k edges), downloaded from `data.pyg.org` at first load (no `torch_geometric` runtime dependency).

## Layout

Matches sibling apps (`arango-dashboard-app`):

| File | Purpose |
|------|---------|
| `app.yaml` | Gunicorn command, env, SQL warehouse resource |
| `deploy_app.sh` | `databricks sync` + `apps deploy` + UC grants |
| `databricks.yml` | Standalone bundle (optional) |
| `resources/bronze_injector.app.yml` | App resource for solo bundle deploy |
| `src/bronze_injector/` | Flask app + playback services |
| `src/wsgi.py` | Gunicorn entry (`PYTHONPATH=src`) |

## Unity Catalog objects

| Object | Default name |
|--------|----------------|
| Volume | `workspace.default.test_bronze_data` → `/Volumes/workspace/default/test_bronze_data` |
| Test source table | `workspace.default.test_bronze_data_elliptic_bitcoin` |
| Bronze playback target | `workspace.default.bronze_elliptic_bitcoin` |
| Playback state | `workspace.default.bronze_injector_playback_state` |
| Demo registry | `workspace.default.demo_tables_registry` |

Registry rows (for jobs/pipelines):

- `category=bronze` → bronze table FQN  
- `category=silver` → `workspace.default.silver_<dataset>` (placeholder until pipeline creates it)  
- `category=gold` / `gold-graphlet` → same pattern  

Pipelines can `SELECT table_name FROM workspace.default.demo_tables_registry WHERE category = 'bronze' AND dataset_key = 'elliptic_bitcoin'`.

## HTTP API (dashboard / curl)

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/api/playback/play` | Start batch append from last `_row_idx` |
| `POST` | `/api/playback/stop` | Stop playback loop |
| `POST` | `/api/playback/reset` | `last_row_idx=0`, `TRUNCATE` bronze table |
| `GET` | `/api/playback/status` | Cursor + row counts |
| `POST` | `/api/dataset/ensure-loaded` | Load test data if empty |
| `GET` | `/api/registry/tables` | List `demo_tables_registry` |

Example (after deploy):

```bash
export INJECTOR_URL="https://....databricksapps.com"
curl -sS -X POST "${INJECTOR_URL}/api/playback/play"
curl -sS -X POST "${INJECTOR_URL}/api/playback/stop"
curl -sS -X POST "${INJECTOR_URL}/api/playback/reset"
```

Wire the dashboard to these endpoints (same auth model as other app-to-app calls: user token or service principal with `CAN_USE` on this app).

## Configuration (`app.yaml` / bundle)

| Env | Default | Meaning |
|-----|---------|---------|
| `DATABRICKS_SQL_WAREHOUSE_ID` | (required) | SQL warehouse for DDL/DML |
| `BRONZE_INJECTOR_DATASET` | `elliptic_bitcoin` | Dataset key (table suffix) |
| `TEST_BRONZE_VOLUME_NAME` | `test_bronze_data` | UC volume name |
| `DEMO_TABLES_REGISTRY_TABLE` | `workspace.default.demo_tables_registry` | Medallion name registry |
| `PLAYBACK_BATCH_SIZE` | `200` | Rows per PLAY tick |
| `PLAYBACK_INTERVAL_SEC` | `0.25` | Sleep between batches |
| `AUTO_ENSURE_DATASET_ON_STARTUP` | `true` | Background load on boot |

## Deploy

**Solo:**

```bash
export DATABRICKS_SQL_WAREHOUSE_ID=<warehouse-hex>
./deploy_app.sh
```

**Platform bundle** (`arango-platform-bundle`): symlink `apps/arango-bronze-simulated-injector` → this repo; `databricks bundle deploy -t dev` deploys with gateway, agent, and dashboard.

App name: `arango-bronze-injector` (≤26 chars). Bundle target suffix: `arango-bronze-injector-dev`.

**Note:** Gunicorn runs with `--workers 1` so a single in-process playback thread is authoritative.

## First load

On startup (or `POST /api/dataset/ensure-loaded`), if the test source table is empty the app downloads the Elliptic zip, inserts nodes then edges with monotonic `_row_idx`, creates the bronze table schema, and registers names in `demo_tables_registry`. Large download — allow several minutes on first run.
