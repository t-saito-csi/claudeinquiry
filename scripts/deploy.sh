#!/usr/bin/env bash
# deploy.sh — OCI Compute Instance上で実行されるデプロイスクリプト
# GitHub Actionsからssh経由で呼び出される
# 環境変数:
#   DEPLOY_SHA  - デプロイするGitコミットSHA (GitHub Actionsが設定)

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/claudeinquiry}"
REGISTRY="ghcr.io"
IMAGE_OWNER="t-saito-csi"
IMAGE_REPO="claudeinquiry"

echo "[deploy] Starting deployment at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "[deploy] Commit SHA: ${DEPLOY_SHA:-unknown}"

# --- 1. リポジトリを最新化 ---
echo "[deploy] Pulling latest code..."
cd "$REPO_DIR"
git fetch origin main
git reset --hard origin/main

# --- 2. GHCR からイメージをプル ---
echo "[deploy] Pulling Docker images from GHCR..."
docker compose -f docker-compose.prod.yml pull

# --- 3. コンテナを再起動（ダウンタイム最小化: --no-deps で依存コンテナは維持） ---
echo "[deploy] Restarting services..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# --- 4. ヘルスチェック：APIが起動するまで待機（最大60秒） ---
echo "[deploy] Waiting for API health check..."
MAX_WAIT=60
ELAPSED=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo "[deploy] ERROR: API did not become healthy within ${MAX_WAIT}s"
    docker compose -f docker-compose.prod.yml logs --tail=50 api
    exit 1
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
echo "[deploy] API is healthy."

# --- 5. 古いイメージの削除（ディスク節約） ---
echo "[deploy] Pruning dangling images..."
docker image prune -f

echo "[deploy] Deployment complete at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
