#!/bin/bash
# Info-Hub 后端服务启动脚本
# 用法: ./start.sh [start|stop|restart|status]

set -e

APP_NAME="info-hub-backend"
PID_FILE="/tmp/${APP_NAME}.pid"
LOG_FILE="/tmp/${APP_NAME}.out.log"
WORKERS=1
HOST="0.0.0.0"
PORT=8001

# 激活虚拟环境
VENV_DIR="$(cd "$(dirname "$0")" && pwd)/.venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "错误: 虚拟环境不存在，请先运行: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "服务已在运行 (PID: $PID)"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "启动 $APP_NAME (端口 $PORT)..."
    nohup uvicorn main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level info \
        > "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    echo "服务已启动 (PID: $(cat "$PID_FILE"))"
    echo "日志: tail -f $LOG_FILE"
    echo "健康检查: curl http://127.0.0.1:$PORT/api/health"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "停止服务 (PID: $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "服务已停止"
        else
            echo "服务未运行 (PID 文件存在但进程不存在)"
            rm -f "$PID_FILE"
        fi
    else
        echo "服务未运行"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "服务运行中 (PID: $PID)"
            echo "端口: $PORT"
            echo "日志: $LOG_FILE"
            return 0
        else
            echo "服务已停止 (残留 PID 文件)"
            return 1
        fi
    else
        echo "服务未运行"
        return 1
    fi
}

restart() {
    stop
    sleep 2
    start
}

case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
