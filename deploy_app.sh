#!/usr/bin/env bash
set -euo pipefail

# Deploy arango-bronze-injector (simulated bronze playback app).
#
#   ./deploy_app.sh
#   ./deploy_app.sh arango-bronze-injector-dev /Workspace/Users/you/arango-bronze-injector myprofile
#
# Set DATABRICKS_SQL_WAREHOUSE_ID or pass as 7th positional arg.

APP_NAME="${1:-arango-bronze-injector}"
PROFILE="${3:-}"

_resolve_ws_user() {
  local args=() user_json user
  [[ -n "${PROFILE}" ]] && args=(--profile "${PROFILE}")
  user_json="$(databricks current-user me "${args[@]}" 2>/dev/null)" || return 1
  user="$(printf '%s' "${user_json}" | python3 -c 'import json,sys; d=json.load(sys.stdin); e=d.get("emails") or []; print(d.get("userName") or (e[0].get("value") if e else ""))' 2>/dev/null)" || return 1
  [[ -n "${user}" ]] || return 1
  printf '%s' "${user}"
}

if [[ -n "${2:-}" ]]; then
  SOURCE_CODE_PATH="$2"
else
  _ws_user="$(_resolve_ws_user)" || {
    echo "ERROR: could not resolve workspace user." >&2
    echo "Pass source path: ./deploy_app.sh ${APP_NAME} /Workspace/Users/<you>/${APP_NAME}" >&2
    exit 1
  }
  SOURCE_CODE_PATH="/Workspace/Users/${_ws_user}/${APP_NAME}"
fi

WAREHOUSE_ID="${DATABRICKS_SQL_WAREHOUSE_ID:-${7:-}}"
DEMO_REGISTRY="${DEMO_TABLES_REGISTRY_TABLE:-workspace.default.demo_tables_registry}"
CATALOG="${BRONZE_INJECTOR_CATALOG:-workspace}"
SCHEMA="${BRONZE_INJECTOR_SCHEMA:-default}"
VOLUME="${TEST_BRONZE_VOLUME_NAME:-test_bronze_data}"
INJECTOR_REGISTRY_TABLE="${ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE:-workspace.default.arango_bronze_simulated_injector_registry}"
PLAYBACK_TBL="${PLAYBACK_STATE_TABLE:-workspace.default.arango_bronze_simulated_injector_playback_state}"
BRONZE_RAW_TBL="${BRONZE_RAW_DATA_TABLE:-${CATALOG}.${SCHEMA}.bronze_raw_data}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "${SCRIPT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python3"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python3" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python3"
else
  PYTHON_BIN="python3"
fi

if [[ -n "${PROFILE}" ]]; then
  PROFILE_ARGS=(--profile "${PROFILE}")
else
  PROFILE_ARGS=()
fi

ensure_app_running_before_deploy() {
  local json app_state
  if ! json="$(databricks apps get "${APP_NAME}" --output json "${PROFILE_ARGS[@]}" 2>/dev/null)"; then
    return 0
  fi
  app_state="$(
    "${PYTHON_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print((d.get("app_status") or {}).get("state",""))' <<< "${json}" 2>/dev/null || true
  )"
  if [[ "${app_state}" == "RUNNING" ]]; then
    return 0
  fi
  echo "Starting app '${APP_NAME}' before deploy..."
  databricks apps start "${APP_NAME}" "${PROFILE_ARGS[@]}"
}

run_sql_statement() {
  local statement="$1"
  local payload
  payload="$(
    "${PYTHON_BIN}" -c 'import json,sys; print(json.dumps({"warehouse_id":sys.argv[1], "statement":sys.argv[2], "wait_timeout":"50s"}))' \
      "${WAREHOUSE_ID}" "${statement}"
  )"
  local response statement_id status
  response="$(databricks api post /api/2.0/sql/statements --json "${payload}" "${PROFILE_ARGS[@]}")"
  statement_id="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin).get("statement_id",""))' <<< "${response}")"
  status="$("${PYTHON_BIN}" -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("state",""))' <<< "${response}")"
  if [[ -z "${statement_id}" ]]; then
    echo "ERROR: SQL statement did not return statement_id" >&2
    exit 1
  fi
  for _ in $(seq 1 60); do
    if [[ "${status}" == "SUCCEEDED" ]]; then
      return 0
    fi
    if [[ "${status}" == "FAILED" || "${status}" == "CANCELED" || "${status}" == "CLOSED" ]]; then
      echo "ERROR: SQL ${statement_id} status=${status}" >&2
      exit 1
    fi
    sleep 1
    response="$(databricks api get "/api/2.0/sql/statements/${statement_id}" "${PROFILE_ARGS[@]}")"
    status="$("${PYTHON_BIN}" -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("state",""))' <<< "${response}")"
  done
  echo "ERROR: SQL timed out" >&2
  exit 1
}

echo "Syncing to ${SOURCE_CODE_PATH}..."
databricks sync . "${SOURCE_CODE_PATH}" "${PROFILE_ARGS[@]}"

if ! databricks apps get "${APP_NAME}" "${PROFILE_ARGS[@]}" &>/dev/null; then
  echo "Creating Databricks App '${APP_NAME}'..."
  databricks apps create "${APP_NAME}" \
    --description "Simulated bronze injector — load test dataset and playback into bronze tables" \
    "${PROFILE_ARGS[@]}"
fi

ensure_app_running_before_deploy

echo "Deploying '${APP_NAME}'..."
databricks apps deploy "${APP_NAME}" \
  --source-code-path "${SOURCE_CODE_PATH}" \
  "${PROFILE_ARGS[@]}"

APP_JSON="$(databricks apps get "${APP_NAME}" --output json "${PROFILE_ARGS[@]}")"
APP_URL="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin).get("url",""))' <<< "${APP_JSON}")"
APP_SP="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin).get("service_principal_client_id",""))' <<< "${APP_JSON}")"

if [[ -z "${WAREHOUSE_ID// }" ]]; then
  echo "ERROR: DATABRICKS_SQL_WAREHOUSE_ID is not set." >&2
  exit 1
fi

if [[ -z "${APP_SP}" ]]; then
  echo "ERROR: Could not read app service principal client id." >&2
  exit 1
fi

# Pre-create schemas/tables as the deploying identity (typically your user) so subsequent
# GRANTs to ``account users`` succeed and UC UI lists tables for human operators.
# Matches arango-gateway-app deploy_app.sh pattern.
grant_account_users_on_table() {
  local t="$1"
  (
    run_sql_statement "GRANT SELECT, MODIFY ON TABLE ${t} TO \`account users\`"
  ) || echo "NOTE: GRANT \`account users\` ON TABLE ${t} failed (principal disabled, not owner yet, or metastore policy)." >&2
}

grant_read_volume_account_users() {
  (
    run_sql_statement "GRANT READ VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \`account users\`"
  ) || echo "NOTE: GRANT READ VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \`account users\` failed." >&2
}

echo "Pre-creating UC schema, volume, and injector Delta tables for deploy-time ownership + human visibility..."
run_sql_statement "CREATE SCHEMA IF NOT EXISTS \`${CATALOG}\`.\`${SCHEMA}\`"
run_sql_statement "CREATE VOLUME IF NOT EXISTS \`${CATALOG}\`.\`${SCHEMA}\`.\`${VOLUME}\`"

run_sql_statement "CREATE TABLE IF NOT EXISTS ${DEMO_REGISTRY} (
  category STRING NOT NULL,
  table_name STRING NOT NULL,
  dataset_key STRING,
  description STRING,
  updated_at TIMESTAMP NOT NULL
) USING DELTA"

run_sql_statement "CREATE TABLE IF NOT EXISTS ${PLAYBACK_TBL} (
  dataset_key STRING NOT NULL,
  last_row_idx BIGINT NOT NULL,
  is_playing BOOLEAN NOT NULL,
  playback_file_marker STRING,
  updated_at TIMESTAMP NOT NULL
) USING DELTA"

run_sql_statement "CREATE TABLE IF NOT EXISTS ${INJECTOR_REGISTRY_TABLE} (
  base_url STRING NOT NULL,
  app_name STRING NOT NULL,
  is_active BOOLEAN NOT NULL,
  status STRING NOT NULL,
  playback_status STRING,
  dataset_key STRING,
  status_detail STRING,
  updated_at TIMESTAMP NOT NULL
) USING DELTA"

run_sql_statement "CREATE TABLE IF NOT EXISTS ${BRONZE_RAW_TBL} (
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
) USING DELTA"

echo "Granting SELECT, MODIFY on injector UC tables to \`account users\` (operators can inspect in UC)..."
grant_account_users_on_table "${DEMO_REGISTRY}"
grant_account_users_on_table "${PLAYBACK_TBL}"
grant_account_users_on_table "${INJECTOR_REGISTRY_TABLE}"
grant_account_users_on_table "${BRONZE_RAW_TBL}"
grant_read_volume_account_users

echo "Granting UC privileges to app SP..."
run_sql_statement "GRANT USE CATALOG ON CATALOG ${CATALOG} TO \`${APP_SP}\`"
run_sql_statement "GRANT USE SCHEMA ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
run_sql_statement "GRANT CREATE TABLE ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
run_sql_statement "GRANT CREATE VOLUME ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
if ! run_sql_statement "GRANT READ VOLUME, WRITE VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \`${APP_SP}\`" 2>/dev/null; then
  echo "NOTE: volume grant deferred until ${CATALOG}.${SCHEMA}.${VOLUME} exists (first app startup)." >&2
fi

for tbl in "${DEMO_REGISTRY}" "${PLAYBACK_TBL}" "${INJECTOR_REGISTRY_TABLE}" "${BRONZE_RAW_TBL}"; do
  if run_sql_statement "GRANT SELECT, MODIFY ON TABLE ${tbl} TO \`${APP_SP}\`" 2>/dev/null; then
    :
  else
    echo "NOTE: GRANT SP on ${tbl} failed (often ok if metastore denies until owner aligns)." >&2
  fi
done

echo "(Re)tolerant grant \`account users\` — covers tables created earlier by app SP:"
grant_account_users_on_table "${DEMO_REGISTRY}"
grant_account_users_on_table "${PLAYBACK_TBL}"
grant_account_users_on_table "${INJECTOR_REGISTRY_TABLE}"
grant_account_users_on_table "${BRONZE_RAW_TBL}"
grant_read_volume_account_users

echo
echo "DATABRICKS_APP_URL=${APP_URL}"
echo "Playback API: POST ${APP_URL}/api/playback/play | stop | reset"
echo "Dataset load: POST ${APP_URL}/api/dataset/ensure-loaded"
echo "Registry: GET ${APP_URL}/api/registry/tables"

UPDATE_REG_SCRIPT="${SCRIPT_DIR}/update_arango_bronze_simulated_injector_registry_uc.sh"
if [[ -x "${UPDATE_REG_SCRIPT}" ]]; then
  echo "Publishing injector URL + status to UC (${INJECTOR_REGISTRY_TABLE})..."
  if DATABRICKS_APP_URL="${APP_URL}" \
    DATABRICKS_APP_NAME="${APP_NAME}" \
    ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE="${INJECTOR_REGISTRY_TABLE}" \
    DATABRICKS_SQL_WAREHOUSE_ID="${WAREHOUSE_ID}" \
    APP_SERVICE_PRINCIPAL_CLIENT_ID="${APP_SP}" \
    "${UPDATE_REG_SCRIPT}" "${APP_URL}" "${APP_NAME}" "${INJECTOR_REGISTRY_TABLE}" "${WAREHOUSE_ID}" "${PROFILE}" "${APP_SP}"; then
    :
  else
    echo "NOTE: UC registry upsert failed; app publishes on startup via ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_AUTO_CREATE." >&2
  fi
else
  echo "NOTE: update_arango_bronze_simulated_injector_registry_uc.sh missing or not executable; skip UC publish script." >&2
fi

