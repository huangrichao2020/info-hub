"""
Info-Hub 全局配置
- 注入 uwillberich 模块路径到 sys.path
- 加载环境变量（API Keys）
- 定义路径常量
"""
import os
import sys
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────
HOME = Path.home()
UWILLBERICH_SKILL_ROOT = HOME / "Desktop" / "uwillberich" / "skill" / "uwillberich"
UWILLBERICH_SCRIPTS = HOME / "Desktop" / "uwillberich" / "skill" / "uwillberich" / "scripts"
UWILLBERICH_KNOWLEDGE = UWILLBERICH_SKILL_ROOT / "knowledge"
UWILLBERICH_ASSETS = UWILLBERICH_SKILL_ROOT / "assets"
INFOHUB_DATA_DIR = HOME / ".info-hub"
INFOHUB_DB_PATH = INFOHUB_DATA_DIR / "info_hub.sqlite3"
_uw_news_candidates = [
    HOME / ".uwillberich" / "news-collector" / "news.sqlite3",
    UWILLBERICH_SCRIPTS / "news.sqlite3",
]
_uw_iterator_candidates = [
    HOME / ".uwillberich" / "news-iterator" / "news_iterator.sqlite3",
    UWILLBERICH_SCRIPTS / "news.sqlite3",
]
UWILLBERICH_NEWS_DB = next((path for path in _uw_news_candidates if path.exists()), _uw_news_candidates[0])
UWILLBERICH_ITERATOR_DB = next((path for path in _uw_iterator_candidates if path.exists()), _uw_iterator_candidates[0])
UWILLBERICH_LATEST_NEWS_JSON = UWILLBERICH_SCRIPTS / "latest_news.json"

# ── 注入 uwillberich 到 sys.path ─────────────────────────
if str(UWILLBERICH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UWILLBERICH_SCRIPTS))

# ── 加载环境变量 ──────────────────────────────────────────
def _load_env_file(path: Path):
    """从 .env 文件加载环境变量（不覆盖已有的）"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value

# 加载 uwillberich 运行时环境
_load_env_file(HOME / ".uwillberich" / "runtime.env")
# 加载 Qwen DashScope key
_load_env_file(HOME / "Desktop" / "uwillberich" / ".qwen-env")
# 加载本地 shell profile 中的问财等环境变量
_load_env_file(HOME / ".zshrc")
_load_env_file(HOME / ".bash_profile")

# ── DashScope / Qwen 配置 ────────────────────────────────
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = "qwen3-coder-plus"

# ── 确保数据目录存在 ──────────────────────────────────────
INFOHUB_DATA_DIR.mkdir(parents=True, exist_ok=True)
