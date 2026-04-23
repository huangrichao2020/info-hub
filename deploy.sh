#!/bin/bash
set -e

APP_DIR="/home/deploy/info-hub"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
FRONTEND_DIST="/www/wwwroot/info-hub"
BACKEND_PORT=8001
PID_FILE="/tmp/info-hub-backend.pid"
LOG_FILE="/tmp/info-hub-backend.log"

cd "$APP_DIR"

echo "[deploy] pulling latest code..."
git fetch origin main
git reset --hard origin/main

COMMIT=$(git rev-parse --short HEAD)
TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "no-tag")
DATE=$(git log -1 --format='%ci' | cut -d' ' -f1-2)

echo "[deploy] version: $TAG @ $COMMIT ($DATE)"

# 写入版本信息到后端
VERSION_JSON="{\"version\":\"$TAG\",\"commit\":\"$COMMIT\",\"date\":\"$DATE\",\"deploy_time\":\"$(date -Iseconds)\"}"
echo "$VERSION_JSON" > "$BACKEND_DIR/version_info.json"

# 构建前端
echo "[deploy] building frontend..."
cd "$FRONTEND_DIR"
npm install --silent 2>&1 | tail -3
npm run build 2>&1 | tail -5

# 写入构建版本号到前端源码（下次构建时生效）
cat > "$FRONTEND_DIR/src/version.ts" << EOF
export const BUILD_VERSION = "$TAG";
export const BUILD_COMMIT = "$COMMIT";
export const BUILD_DATE = "$DATE";
EOF

echo "[deploy] deploying frontend to $FRONTEND_DIST..."
rm -rf "$FRONTEND_DIST"/*
cp -r "$FRONTEND_DIR/dist/"* "$FRONTEND_DIST/"

# 重启后端
echo "[deploy] restarting backend..."
cd "$BACKEND_DIR"
source "$BACKEND_DIR/.venv/bin/activate"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$OLD_PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

nohup uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --workers 1 > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

# 等待后端启动
for i in $(seq 1 15); do
    if curl -sf http://127.0.0.1:$BACKEND_PORT/api/health >/dev/null 2>&1; then
        echo "[deploy] backend started successfully (PID: $(cat $PID_FILE))"
        break
    fi
    sleep 1
done

# 重载 nginx
echo "[deploy] reloading nginx..."
sudo nginx -s reload 2>/dev/null || echo "[warn] nginx reload failed"

echo "[deploy] done! $TAG @ $COMMIT"
