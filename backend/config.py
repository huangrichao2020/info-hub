"""
Info-Hub 全局配置（沙箱环境适配版）
- 加载环境变量（API Keys）
- 定义路径常量
- 适配沙箱/服务器环境，无 macOS Desktop 路径依赖
"""
import os
import sys
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────
HOME = Path.home()
PROJECT_ROOT = Path(__file__).parent.parent  # info-hub/
BACKEND_DIR = Path(__file__).parent          # info-hub/backend/
INFOHUB_DATA_DIR = HOME / ".info-hub"
INFOHUB_DB_PATH = INFOHUB_DATA_DIR / "info_hub.sqlite3"

# uwillberich 相关路径（沙箱中可能不存在，做优雅降级）
UWILLBERICH_SKILL_ROOT = HOME / ".uwillberich"
UWILLBERICH_SCRIPTS = UWILLBERICH_SKILL_ROOT / "scripts"
UWILLBERICH_KNOWLEDGE = UWILLBERICH_SKILL_ROOT / "knowledge"
UWILLBERICH_ASSETS = UWILLBERICH_SKILL_ROOT / "assets"

_uw_news_candidates = [
    HOME / ".uwillberich" / "news-collector" / "news.sqlite3",
    UWILLBERICH_SCRIPTS / "news.sqlite3",
    BACKEND_DIR / "data" / "news.sqlite3",
]
_uw_iterator_candidates = [
    HOME / ".uwillberich" / "news-iterator" / "news_iterator.sqlite3",
    UWILLBERICH_SCRIPTS / "news.sqlite3",
    BACKEND_DIR / "data" / "news.sqlite3",
]
UWILLBERICH_NEWS_DB = next((path for path in _uw_news_candidates if path.exists()), BACKEND_DIR / "data" / "news.sqlite3")
UWILLBERICH_ITERATOR_DB = next((path for path in _uw_iterator_candidates if path.exists()), BACKEND_DIR / "data" / "news.sqlite3")
UWILLBERICH_LATEST_NEWS_JSON = BACKEND_DIR / "data" / "latest_news.json"

# ── 注入 uwillberich 到 sys.path（如果存在）───────────────
if UWILLBERICH_SCRIPTS.exists() and str(UWILLBERICH_SCRIPTS) not in sys.path:
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

# 加载环境变量（多来源，优雅降级）
_load_env_file(BACKEND_DIR / ".env")          # backend/.env
_load_env_file(HOME / ".uwillberich" / "runtime.env")
_load_env_file(HOME / ".zshrc")
_load_env_file(HOME / ".bash_profile")

# ── DashScope / Qwen 配置 ────────────────────────────────
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", os.environ.get("AUXILIARY_VISION_API_KEY", ""))
DASHSCOPE_BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", os.environ.get("AUXILIARY_VISION_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"))
QWEN_MODEL = "qwen3-coder-plus"

# ── 确保数据目录存在 ──────────────────────────────────────
INFOHUB_DATA_DIR.mkdir(parents=True, exist_ok=True)
(BACKEND_DIR / "data").mkdir(parents=True, exist_ok=True)
