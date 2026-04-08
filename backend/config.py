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
UWILLBERICH_SCRIPTS = HOME / "Desktop" / "uwillberich" / "skill" / "uwillberich" / "scripts"
UWILLBERICH_ASSETS = HOME / "Desktop" / "uwillberich" / "skill" / "uwillberich" / "assets"
INFOHUB_DATA_DIR = HOME / ".info-hub"
INFOHUB_DB_PATH = INFOHUB_DATA_DIR / "info_hub.sqlite3"
UWILLBERICH_NEWS_DB = HOME / ".uwillberich" / "news-collector" / "news.sqlite3"
UWILLBERICH_ITERATOR_DB = HOME / ".uwillberich" / "news-iterator" / "news_iterator.sqlite3"

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

# ── DashScope / Qwen 配置 ────────────────────────────────
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

# ── 确保数据目录存在 ──────────────────────────────────────
INFOHUB_DATA_DIR.mkdir(parents=True, exist_ok=True)
