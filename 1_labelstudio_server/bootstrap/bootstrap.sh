#!/bin/sh
set -eu

BASE="${LS_BASE%/}"

# --- Wait for Label Studio to be ready ---
echo "[bootstrap] Waiting for Label Studio to finish initializing..."
until curl -fsS "$BASE/api/version" | grep -q '"version"'; do
  echo "[bootstrap] Still waiting for Label Studio..."
  sleep 5
done
echo "[bootstrap] Label Studio API responding."

# Small extra delay for DB initialization
sleep 5
echo "[bootstrap] Label Studio is fully ready."


echo "[bootstrap] Starting bootstrap process..."

# --- Auth header (legacy token) ---
if [ -n "${LS_TOKEN:-}" ]; then
  AUTH="Authorization: Token ${LS_TOKEN}"
else
  echo "[bootstrap] ERROR: LS_TOKEN is not set; cannot authenticate."
  exit 1
fi

JSON="Content-Type: application/json"

# --- Step 3: Ensure project exists ---
echo "[bootstrap] Ensuring project exists..."
PROJECT_ID=$(
  curl -fsS "$BASE/api/projects/?title=$(printf %s "$PROJECT_TITLE" | sed 's/ /%20/g')" -H "$AUTH" \
    | awk 'match($0,/"id":[ ]*([0-9]+)/){print substr($0,RSTART+5,RLENGTH-5)}' | head -n1
)

if [ -z "${PROJECT_ID:-}" ]; then
  echo "[bootstrap] Creating project: $PROJECT_TITLE"

  LABEL_CONFIG_PATH="/bootstrap/label_config.xml"
  if [ ! -f "$LABEL_CONFIG_PATH" ]; then
    echo "[bootstrap] ERROR: label_config.xml not found at $LABEL_CONFIG_PATH"
    exit 1
  fi

  LABEL_CONFIG=$(sed ':a;N;$!ba;s/\\/\\\\/g;s/\"/\\\"/g;s/\n/ /g' "$LABEL_CONFIG_PATH")

  printf '%s\n' "{
    \"title\": \"${PROJECT_TITLE}\",
    \"description\": \"${PROJECT_DESC}\",
    \"label_config\": \"${LABEL_CONFIG}\"
  }" > /tmp/project_payload.json

  RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/project_response.json \
    -X POST "$BASE/api/projects/" -H "$AUTH" -H "$JSON" -d @/tmp/project_payload.json)

  if [ "$RESPONSE" != "201" ]; then
    echo "[bootstrap] ERROR: Project creation failed (HTTP $RESPONSE)"
    cat /tmp/project_response.json
    exit 1
  fi

  PROJECT_ID=$(awk 'match($0,/"id":[ ]*([0-9]+)/){print substr($0,RSTART+5,RLENGTH-5)}' /tmp/project_response.json)
  echo "[bootstrap] Project created id=$PROJECT_ID"
else
  echo "[bootstrap] Project found id=$PROJECT_ID"
fi

# --- Step 4: Ensure Local Files import storage exists ---
echo "[bootstrap] Ensuring Local Files import storage..."
STORAGE_ID=$(
  curl -fsS "$BASE/api/storages/localfiles/?project=$PROJECT_ID" -H "$AUTH" \
    | awk 'match($0,/"id":[ ]*([0-9]+)/){print substr($0,RSTART+5,RLENGTH-5)}' | head -n1
)

if [ -z "${STORAGE_ID:-}" ]; then
  PAYLOAD=$(cat <<EOF
{"title":"Local repository","project":$PROJECT_ID,"path":"${LOCAL_SOURCE_PATH}","regex_filter":".*","use_blob_urls":true,"recursive_scan":true}
EOF
)
  STORAGE_ID=$(
    echo "$PAYLOAD" | curl -fsS -X POST "$BASE/api/storages/localfiles/" \
      -H "$AUTH" -H "$JSON" -d @- \
      | awk 'match($0,/"id":[ ]*([0-9]+)/){print substr($0,RSTART+5,RLENGTH-5)}'
  )
  echo "[bootstrap] Created storage id=$STORAGE_ID"
else
  echo "[bootstrap] Storage found id=$STORAGE_ID"
fi

# --- Step 5: Sync storage ---
echo "[bootstrap] Syncing storage..."
curl -fsS -X POST "$BASE/api/storages/localfiles/$STORAGE_ID/sync" -H "$AUTH" >/dev/null
echo "[bootstrap] Done."
