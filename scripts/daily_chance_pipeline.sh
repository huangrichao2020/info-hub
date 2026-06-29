#!/bin/bash
# 每日机会扫描 · 自动化 pipeline
# 流程: API 扫描 → JSON 归档 → HTML 报告 → commit + push
# 触发: cron daily-chance-scan (工作日 8:30 Asia/Shanghai)

set -e

# ===== 路径配置 =====
INFO_HUB_ROOT="/Users/tingchi/Desktop/info-hub"
SCRIPTS_DIR="$INFO_HUB_ROOT/scripts"
ARCHIVE_ROOT="$INFO_HUB_ROOT/股票研究/daily-chance"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)
ARCHIVE_DIR="$ARCHIVE_ROOT/$DATE"
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"
LOG_FILE="$ARCHIVE_ROOT/pipeline.log"

mkdir -p "$ARCHIVE_DIR"
mkdir -p "$(dirname $LOG_FILE)"

log() {
  echo "[$DATE $TIME] $1" | tee -a "$LOG_FILE"
}

log "==== 每日机会扫描 pipeline 启动 ===="

# ===== Step 1: 调 API 扫描 =====
log "Step 1: 调用 $BACKEND_URL/api/daily-chance/today"
if ! curl -sf "$BACKEND_URL/api/daily-chance/today" -o "$ARCHIVE_DIR/data.json"; then
  log "ERROR: API 调用失败，请检查后端服务是否启动"
  exit 1
fi
log "  ✅ data.json 已保存 ($(wc -c < $ARCHIVE_DIR/data.json) bytes)"

# ===== Step 2: 生成 HTML 报告 =====
log "Step 2: 生成 HTML 报告"
python3 "$SCRIPTS_DIR/gen_daily_chance_report.py" "$ARCHIVE_DIR/data.json" 2>&1 | tee -a "$LOG_FILE"

# ===== Step 2.5: 同步到 Obsidian vault =====
log "Step 2.5: 同步到 Obsidian vault (Karpathy LLM Wiki 范式)"
if command -v python3 >/dev/null 2>&1; then
  # 用 exec 包装避免 Python 3.14 中文路径问题
  python3 -c "
import sys
sys.path.insert(0, '$SCRIPTS_DIR')
exec(open('$SCRIPTS_DIR/obsidian_sync.py').read())
" "$ARCHIVE_DIR/data.json" 2>&1 | tee -a "$LOG_FILE"
  log "  ✅ Obsidian 同步完成"
else
  log "  ⚠️ python3 未找到，跳过 Obsidian 同步"
fi

# ===== Step 3: 检查是否有变化 =====
cd "$INFO_HUB_ROOT"
if git diff --quiet "股票研究/daily-chance/$DATE/" 2>/dev/null; then
  log "Step 3: 数据无变化，跳过 commit"
  exit 0
fi

# ===== Step 4: commit + push =====
log "Step 4: git add + commit + push"
git add "股票研究/daily-chance/$DATE/"

# 提取 S 级数量作为 commit message 一部分
S_COUNT=$(python3 -c "import json; d=json.load(open('$ARCHIVE_DIR/data.json'))['data']; print(d['stats']['s_count'])" 2>/dev/null || echo "?")
A_COUNT=$(python3 -c "import json; d=json.load(open('$ARCHIVE_DIR/data.json'))['data']; print(d['stats']['a_count'])" 2>/dev/null || echo "?")
B_COUNT=$(python3 -c "import json; d=json.load(open('$ARCHIVE_DIR/data.json'))['data']; print(d['stats']['b_count'])" 2>/dev/null || echo "?")

COMMIT_MSG="chore(每日机会): 自动归档 $DATE · S $S_COUNT / A $A_COUNT / B $B_COUNT"
git commit -m "$COMMIT_MSG" 2>&1 | tee -a "$LOG_FILE"

if git push origin main 2>&1 | tee -a "$LOG_FILE"; then
  log "  ✅ 已 push 到 origin/main"
else
  log "  ⚠️ push 失败（commit 已成功，本地有记录）"
  exit 1
fi

log "==== pipeline 完成 ===="