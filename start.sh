#!/usr/bin/env bash
# Bring up Synapse-RAG: init DB (create + migrate) -> seed admin ->
# gate on Ollama -> docker compose up -d --build.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { cp .env.example .env; echo "created .env — edit it and rerun ./start.sh"; exit 1; }
command -v docker >/dev/null || { echo "docker is required"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose is required"; exit 1; }

set -a
# Quote-tolerant .env loader (`source` would expand $ and break on spaces).
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|\#*) continue ;; esac
  case "$line" in *=*) ;; *) continue ;; esac
  key=${line%%=*}
  val=${line#*=}
  case "$val" in
    "'"*"'") val=${val#\'}; val=${val%\'} ;;
    '"'*'"') val=${val#\"}; val=${val%\"} ;;
  esac
  printf -v "$key" '%s' "$val" && export "$key"
done < .env
set +a
: "${DATABASE_NAME:?DATABASE_NAME missing in .env}"
: "${DATABASE_USER:?DATABASE_USER missing in .env}"
: "${DATABASE_PASSWORD:?DATABASE_PASSWORD missing in .env}"
: "${OLLAMA_URL:?OLLAMA_URL missing in .env}"
: "${DATABASE_HOST:?DATABASE_HOST missing in .env}"
: "${DATABASE_PORT:?DATABASE_PORT missing in .env}"
echo "db target: $DATABASE_USER@$DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
case "$DATABASE_HOST" in
  localhost|127.0.0.1|::1)
    if [ "${ALLOW_LOCALHOST_DB:-0}" != "1" ]; then
      echo "ABORT: DATABASE_HOST=$DATABASE_HOST is unreachable from containers" \
        "(localhost inside a container is the container itself)."
      echo "If Postgres runs on your machine, use host.docker.internal" \
        "(Docker Desktop) or your LAN IP. Set ALLOW_LOCALHOST_DB=1 to override."
      exit 1
    fi ;;
esac

echo "== 1/4 database =="
docker compose build api
# -e flags forward the sourced .env explicitly (env_file alone is not
# honoured by every `compose run` code path).
docker compose run --rm -v ./infra:/infra \
  -e MIGRATIONS_DIR=/infra/migrations \
  -e DATABASE_HOST -e DATABASE_PORT -e DATABASE_NAME \
  -e DATABASE_USER -e DATABASE_PASSWORD \
  api python /infra/db_init.py

echo "== 2/4 admin seed =="
docker compose run --rm \
  -e DATABASE_HOST -e DATABASE_PORT -e DATABASE_NAME \
  -e DATABASE_USER -e DATABASE_PASSWORD \
  -e JWT_SECRET -e OLLAMA_URL \
  -e SEED_ADMIN_NAME -e SEED_ADMIN_USER -e SEED_ADMIN_PASS \
  api python seed.py

echo "== 3/4 ollama =="
case "$OLLAMA_URL" in
  *localhost*|*127.0.0.1*)
    echo "WARN: OLLAMA_URL=$OLLAMA_URL resolves to each container itself;" \
      "containers need host.docker.internal or a LAN IP." ;;
esac
# Probe from the host perspective: host.docker.internal may not resolve
# natively, so retry as plain localhost (same service, host view).
PROBE_URL="$OLLAMA_URL"
case "$PROBE_URL" in
  *host.docker.internal*) PROBE_URL="${PROBE_URL//host.docker.internal/localhost}" ;;
esac
curl -sf -m 10 "$OLLAMA_URL/api/tags" >/dev/null 2>&1 \
  || curl -sf -m 10 "$PROBE_URL/api/tags" >/dev/null \
  || { echo "ollama not reachable at $OLLAMA_URL — start it first"; exit 1; }
echo "ollama reachable"

echo "== 4/4 compose up =="
docker compose up -d --build
docker compose ps
