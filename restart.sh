#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-entrance-observer}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
LEGACY_PROJECT_NAME="${LEGACY_PROJECT_NAME:-gratheon}"
SERVICE_NAME="${SERVICE_NAME:-entrance-observer}"

cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

stop_legacy_gratheon_service_container() {
  docker ps -aq \
    --filter "label=com.docker.compose.project=${LEGACY_PROJECT_NAME}" \
    --filter "label=com.docker.compose.service=${SERVICE_NAME}" \
    | while IFS= read -r container_id; do
        [ -n "$container_id" ] || continue
        docker rm -f "$container_id" >/dev/null 2>&1 || true
      done
}

stop_legacy_gratheon_service_container

# WHY: never use --remove-orphans with the legacy gratheon project name. It can
# delete unrelated production containers that still share that project label.
COMPOSE_PROJECT_NAME="$PROJECT_NAME" docker compose -f "$COMPOSE_FILE" down --timeout 45
COMPOSE_PROJECT_NAME="$PROJECT_NAME" docker compose -f "$COMPOSE_FILE" up -d --build
