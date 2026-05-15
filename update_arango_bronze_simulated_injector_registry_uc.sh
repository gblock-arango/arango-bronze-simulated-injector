#!/usr/bin/env bash
set -euo pipefail

# Publish the bronze simulated injector Databricks App URL + initial status to Unity Catalog
# (same pattern as update_arango_agent_registry_uc.sh).
#
# Usage:
#   ./update_arango_bronze_simulated_injector_registry_uc.sh [base-url] [app-name] [table] [warehouse-id] [profile] [injector-sp-client-id]
#
# Optional env: INJECTOR_REGISTRY_UC_UPSERT_RETRIES (default 10)

BASE_URL_INPUT="${1:-${DATABRICKS_APP_URL:-}}"
APP_NAME_INPUT="${2:-${DATABRICKS_APP_NAME:-arango-bronze-injector}}"
REGISTRY_TABLE="${3:-${ARANGO_BRONZE_SIMULATED_INJECTOR_REGISTRY_TABLE:-workspace.default.arango_bronze_simulated_injector_registry}}"
WAREHOUSE_ID="${4:-${DATABRICKS_SQL_WAREHOUSE_ID:-}}"
PROFILE="${5:-}"
INJECTOR_SP_ID="${6:-${APP_SERVICE_PRINCIPAL_CLIENT_ID:-}}"

if [[ -z "${BASE_URL_INPUT}" ]]; then
  echo "ERROR: injector base URL required (arg1 or DATABRICKS_APP_URL)." >&2
  exit 1
fi

if [[ -z "${WAREHOUSE_ID// }" ]]; then
  echo "ERROR: SQL warehouse id required (arg4 or DATABRICKS_SQL_WAREHOUSE_ID)." >&2
  exit 1
fi

BASE_URL="${BASE_URL_INPUT%/}"

if [[ -n "${PROFILE}" ]]; then
  PROFILE_ARGS=(--profile "${PROFILE}")
else
  PROFILE_ARGS=()
fi

IFS='.' read -r CATALOG_NAME SCHEMA_NAME TABLE_NAME <<< "${REGISTRY_TABLE}"
if [[ -z "${CATALOG_NAME:-}" || -z "${SCHEMA_NAME:-}" || -z "${TABLE_NAME:-}" ]]; then
  echo "ERROR: REGISTRY_TABLE must be catalog.schema.table" >&2
  exit 1
fi

safe_sql_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

run_sql() {
  local statement="$1"
  local payload
  payload="$(
    python3 -c 'import json,sys; print(json.dumps({"warehouse_id":sys.argv[1], "statement":sys.argv[2], "wait_timeout":"50s"}))' \
      "${WAREHOUSE_ID}" "${statement}"
  )"
  local response
  response="$(databricks api post /api/2.0/sql/statements --json "${payload}" "${PROFILE_ARGS[@]}")"
  local status statement_id
  status="$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("state",""))' <<< "${response}")"
  statement_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("statement_id",""))' <<< "${response}")"
  if [[ -z "${statement_id}" ]]; then
    echo "ERROR: SQL statement did not return statement_id" >&2
    echo "${response}" >&2
    return 1
  fi
  for _ in $(seq 1 60); do
    if [[ "${status}" == "SUCCEEDED" ]]; then
      return 0
    fi
    if [[ "${status}" == "FAILED" || "${status}" == "CANCELED" || "${status}" == "CLOSED" ]]; then
      echo "ERROR: SQL statement ${statement_id} status=${status}" >&2
      databricks api get "/api/2.0/sql/statements/${statement_id}" "${PROFILE_ARGS[@]}" >&2 || true
      return 1
    fi
    sleep 1
    response="$(databricks api get "/api/2.0/sql/statements/${statement_id}" "${PROFILE_ARGS[@]}")"
    status="$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("state",""))' <<< "${response}")"
  done
  echo "ERROR: SQL timed out" >&2
  return 1
}

ESC_URL="$(safe_sql_literal "${BASE_URL}")"
ESC_APP="$(safe_sql_literal "${APP_NAME_INPUT}")"
FQTBL="\`${CATALOG_NAME}\`.\`${SCHEMA_NAME}\`.\`${TABLE_NAME}\`"

echo "Ensuring bronze injector URL registry schema/table exists..."
run_sql "CREATE SCHEMA IF NOT EXISTS \`${CATALOG_NAME}\`.\`${SCHEMA_NAME}\`" || exit 1
run_sql "CREATE TABLE IF NOT EXISTS ${FQTBL} (
  base_url STRING NOT NULL,
  app_name STRING NOT NULL,
  is_active BOOLEAN NOT NULL,
  status STRING NOT NULL,
  playback_status STRING,
  dataset_key STRING,
  status_detail STRING,
  updated_at TIMESTAMP NOT NULL
) USING DELTA" || exit 1

echo "Granting SELECT, MODIFY on ${REGISTRY_TABLE} to \`account users\`..."
if ! ( run_sql "GRANT SELECT, MODIFY ON TABLE ${FQTBL} TO \`account users\`" ); then
  echo "NOTE: GRANT to \`account users\` failed (ignore if you are not table owner)." >&2
fi

echo "Upserting active bronze injector row into ${REGISTRY_TABLE}..."
MERGE_SQL="MERGE INTO ${FQTBL} t USING (
  SELECT
    '${ESC_URL}' AS base_url,
    '${ESC_APP}' AS app_name,
    'READY' AS status,
    'IDLE' AS playback_status,
    CAST(NULL AS STRING) AS dataset_key,
    CAST(NULL AS STRING) AS status_detail,
    current_timestamp() AS updated_at
) s ON t.base_url = s.base_url
WHEN MATCHED THEN UPDATE SET
  app_name = s.app_name,
  is_active = TRUE,
  status = s.status,
  playback_status = s.playback_status,
  dataset_key = s.dataset_key,
  status_detail = s.status_detail,
  updated_at = s.updated_at
WHEN NOT MATCHED THEN INSERT
  (base_url, app_name, is_active, status, playback_status, dataset_key, status_detail, updated_at)
  VALUES (s.base_url, s.app_name, TRUE, s.status, s.playback_status, s.dataset_key, s.status_detail, s.updated_at)
WHEN NOT MATCHED BY SOURCE AND t.is_active = TRUE THEN UPDATE SET
  is_active = FALSE,
  updated_at = current_timestamp()"

UPSERT_ATTEMPTS="${INJECTOR_REGISTRY_UC_UPSERT_RETRIES:-10}"
for attempt in $(seq 1 "${UPSERT_ATTEMPTS}"); do
  if run_sql "${MERGE_SQL}"; then
    break
  fi
  if [[ "${attempt}" -ge "${UPSERT_ATTEMPTS}" ]]; then
    echo "ERROR: injector registry MERGE failed after ${UPSERT_ATTEMPTS} attempts." >&2
    exit 1
  fi
  echo "NOTE: UC MERGE conflict; retrying (${attempt}/${UPSERT_ATTEMPTS})..." >&2
  sleep $((1 + attempt))
done

if [[ -n "${INJECTOR_SP_ID}" ]]; then
  echo "Granting SELECT, MODIFY on ${REGISTRY_TABLE} to injector app SP ${INJECTOR_SP_ID}..."
  run_sql "GRANT SELECT, MODIFY ON TABLE ${FQTBL} TO \`${INJECTOR_SP_ID}\`"
fi

echo "Bronze injector registry updated:"
echo "  base_url=${BASE_URL}"
echo "  app_name=${APP_NAME_INPUT}"
echo "  table=${REGISTRY_TABLE}"
