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

echo "Granting UC privileges to app SP..."
run_sql_statement "GRANT USE CATALOG ON CATALOG ${CATALOG} TO \`${APP_SP}\`"
run_sql_statement "GRANT USE SCHEMA ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
run_sql_statement "GRANT CREATE TABLE ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
run_sql_statement "GRANT CREATE VOLUME ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${APP_SP}\`"
if ! run_sql_statement "GRANT READ VOLUME, WRITE VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \`${APP_SP}\`" 2>/dev/null; then
  echo "NOTE: volume grant deferred until ${CATALOG}.${SCHEMA}.${VOLUME} exists (first app startup)." >&2
fi

for tbl in "${DEMO_REGISTRY}" "workspace.default.bronze_injector_playback_state"; do
  if run_sql_statement "GRANT SELECT, MODIFY ON TABLE ${tbl} TO \`${APP_SP}\`" 2>/dev/null; then
    :
  else
    echo "NOTE: GRANT on ${tbl} deferred until table exists (first app run)." >&2
  fi
done

echo
echo "DATABRICKS_APP_URL=${APP_URL}"
echo "Playback API: POST ${APP_URL}/api/playback/play | stop | reset"
echo "Dataset load: POST ${APP_URL}/api/dataset/ensure-loaded"
echo "Registry: GET ${APP_URL}/api/registry/tables"
