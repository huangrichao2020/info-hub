#!/usr/bin/env python3
"""
Obsidian vault → info-hub repo 反向同步 watcher
================================================

监听 ~/Documents/Obsidian Vault 改动 → 同步到 ~/Desktop/info-hub/股票研究/obsidian-mirror/ → git commit + push

核心设计:
1. vault 是 source of truth（用户编辑权 > 脚本自动更新）
2. 排除脚本生成的目录（每日机会/_index/_meta）→ 不反向同步
3. 增量同步：基于 mtime diff
4. 单次模式 / 持续监听模式（cron 用前者，debug 用后者）
5. 跳过锁文件（避免和 obsidian_*.py 同时写冲突）

排除列表（脚本生成的反向不同步）:
- 10-Wiki/Trading/每日机会/    - 每日 S/A/B 生成
- _meta.md                      - vault 介绍（一次性）
- /_index.md                    - 索引页（自动生成）

反向同步范围（用户可编辑）:
- 10-Wiki/Trading/卡脖子分析/{标的名}.md  - 用户可编辑标的笔记
- 10-Wiki/Methodology/*.md                 - 用户可编辑方法论
- 10-Wiki/Concepts/*.md                    - 用户可编辑概念
- 10-Wiki/Trading/Concepts/*.md            - 用户可编辑赛道
"""
import os
import sys
import time
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

VAULT = Path("/Users/tingchi/Documents/Obsidian Vault")
INFO_HUB = Path("/Users/tingchi/Desktop/info-hub")
MIRROR = INFO_HUB / "股票研究" / "obsidian-mirror"
STATE_FILE = Path("/tmp/obsidian-watcher-state.json")
LOCK_FILE = VAULT / ".mavis-watcher.lock"
LOG_FILE = Path("/tmp/obsidian-watcher.log")

# 排除路径（脚本生成的，不反向同步）
EXCLUDE_PATTERNS = [
    "10-Wiki/Trading/每日机会/",  # 每日 S/A/B 生成
    "_meta.md",                   # vault 介绍
    "/_index.md",                 # 索引页
]


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def should_sync(path: Path) -> bool:
    """判断 vault 文件是否应该反向同步到 info-hub"""
    rel = str(path.relative_to(VAULT))
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel:
            return False
    # 只同步 .md
    if path.suffix != ".md":
        return False
    # 跳过隐藏文件
    if path.name.startswith("."):
        return False
    return True


def load_state() -> dict:
    """加载上次同步状态"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict):
    """保存同步状态"""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def acquire_lock() -> bool:
    """获取锁（避免和正向同步冲突）"""
    if LOCK_FILE.exists():
        # 检查锁是否过期（>30 秒认为已死锁）
        try:
            lock_age = time.time() - LOCK_FILE.stat().st_mtime
            if lock_age < 30:
                return False
        except Exception:
            pass
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    """释放锁"""
    try:
        LOCK_FILE.unlink()
    except Exception:
        pass


def git_in_info_hub(*args) -> subprocess.CompletedProcess:
    """在 info-hub 目录执行 git 命令"""
    return subprocess.run(
        ["git", "-C", str(INFO_HUB)] + list(args),
        capture_output=True, text=True
    )


def copy_file(src: Path) -> Path:
    """复制 vault 文件到 info-hub mirror，返回目标路径"""
    rel = src.relative_to(VAULT)
    target = MIRROR / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, target)
    return target


def batch_commit_push(state: dict, changed_files: list) -> bool:
    """批量 commit + push 所有改动"""
    if not changed_files:
        return False

    # git add 所有目标
    for target in changed_files:
        git_in_info_hub("add", str(target))

    # 检查是否有 staged 改动
    result = git_in_info_hub("diff", "--cached", "--name-only")
    if not result.stdout.strip():
        return False

    # commit
    if len(changed_files) == 1:
        msg = f"vault: {changed_files[0].relative_to(INFO_HUB)}"
    else:
        msg = f"vault: 同步 {len(changed_files)} 个文件 (Obsidian 编辑)"

    commit_result = git_in_info_hub("commit", "-m", msg)
    if commit_result.returncode != 0:
        log(f"  ❌ commit 失败: {commit_result.stderr.strip()[:200]}")
        return False

    # push
    push_result = git_in_info_hub("push", "origin", "main")
    if push_result.returncode != 0:
        log(f"  ⚠️ push 失败: {push_result.stderr.strip()[:200]}")
        return False

    log(f"  ✅ 已 commit + push: {len(changed_files)} 个文件")
    return True


def scan_once() -> int:
    """扫描 vault 一次，批量同步"""
    if not acquire_lock():
        log("锁被占用，跳过本次扫描")
        return 0

    try:
        MIRROR.mkdir(parents=True, exist_ok=True)
        state = load_state()
        changed = []  # 待 commit 的文件列表

        for md_file in VAULT.rglob("*.md"):
            if not should_sync(md_file):
                continue

            try:
                rel = str(md_file.relative_to(VAULT))
                src_mtime = md_file.stat().st_mtime

                # 检查 state 记录的 mtime
                prev_mtime = state.get(rel, 0)
                if prev_mtime >= src_mtime:
                    continue  # 没改动

                # 复制文件 + 加入待 commit 列表
                target = copy_file(md_file)
                changed.append(target)
                state[rel] = src_mtime
            except FileNotFoundError:
                continue
            except Exception as e:
                log(f"  ❌ {md_file}: {e}")

        # 批量 commit + push
        if batch_commit_push(state, changed):
            save_state(state)
            return len(changed)
        return 0
    finally:
        release_lock()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"

    if mode == "watch":
        # 持续监听模式（调试用）
        log("==== Obsidian watcher 启动（持续监听模式）====")
        log(f"Vault: {VAULT}")
        log(f"Mirror: {MIRROR}")
        try:
            while True:
                synced = scan_once()
                if synced:
                    log(f"本次同步 {synced} 个文件")
                time.sleep(30)  # 每 30 秒扫描
        except KeyboardInterrupt:
            log("==== Watcher 停止 ====")
    elif mode == "once":
        # 单次扫描模式（cron 用）
        synced = scan_once()
        if synced:
            log(f"==== 完成: 同步 {synced} 个文件 ====")
        sys.exit(0)
    else:
        print(f"Usage: {sys.argv[0]} [once|watch]")
        sys.exit(1)


if __name__ == "__main__":
    main()