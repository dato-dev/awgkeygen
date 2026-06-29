#!/usr/bin/env bash
# Лёгкий watchdog без отдельного контейнера — для cron на сервере.
# Альтернатива Watchtower из docker-compose-prod.yml (используйте что-то одно).
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-prod.yml}"
IMAGE="${IMAGE:-dato1/awgkeygen-bot:latest}"

cd "$DEPLOY_PATH"

LOCAL_DIGEST=""
if docker image inspect "$IMAGE" &>/dev/null; then
  LOCAL_DIGEST=$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')
fi

docker pull -q "$IMAGE"
REMOTE_DIGEST=$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')

if [[ "$LOCAL_DIGEST" == "$REMOTE_DIGEST" && -n "$LOCAL_DIGEST" ]]; then
  echo "Нет обновлений: $IMAGE"
  exit 0
fi

echo "Новый образ: $REMOTE_DIGEST"
docker compose -f "$COMPOSE_FILE" up -d --no-deps awgkeygen-bot
docker image prune -f
echo "Готово"
