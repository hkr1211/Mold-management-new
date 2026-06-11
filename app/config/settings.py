# app/config/settings.py — 应用全局配置

import os

# ── 应用信息 ──────────────────────────────────────────────
APP_NAME = "蕴杰模具全生命周期管理系统"
APP_VERSION = "1.4.0"
SUPPORT_EMAIL = "jerry.houyong@gmail.com"

# ── 数据库（SQLite） ──────────────────────────────────────
# DB_PATH：SQLite 数据库文件路径，可通过环境变量覆盖
_default_db = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mold_management.db')
DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.abspath(_default_db))

# ── 查询 ──────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 100      # 列表查询默认每页条数
CACHE_TTL_SECONDS = 300      # st.cache_data 默认 TTL（秒）
LOOKUP_CACHE_TTL = 600       # 字典表（状态/位置等）缓存 TTL

# ── 安全 ──────────────────────────────────────────────────
LOGIN_MAX_ATTEMPTS = 5       # 最大失败登录次数
LOGIN_LOCKOUT_SECONDS = 300  # 锁定时长（秒）
PASSWORD_MIN_LENGTH = 8      # 密码最小长度
SESSION_TTL_DAYS = 7         # 登录会话有效期（天），到期需重新登录
