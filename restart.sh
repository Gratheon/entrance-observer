#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gratheon}"

docker compose down --timeout 45 --remove-orphans
docker compose up -d --build --remove-orphans
