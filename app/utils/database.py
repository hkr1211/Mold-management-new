# app/utils/database.py — SQLite 本地数据库版
import os
import sqlite3
import threading
import streamlit as st
import logging
import re as _re
import numpy as np
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal

try:
    from config.settings import DB_PATH, CACHE_TTL_SECONDS
except ImportError:
    _default_db = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mold_management.db')
    DB_PATH = os.getenv('SQLITE_DB_PATH', os.path.abspath(_default_db))
    CACHE_TTL_SECONDS = 300

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 连接管理（每线程独立连接 + WAL 模式）────────────────────────────
_local = threading.local()

def _get_conn() -> sqlite3.Connection:
    conn = getattr(_local, 'conn', None)
    if conn is None:
        db_dir = os.path.dirname(os.path.abspath(DB_PATH))
        os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False,
                               detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=NORMAL')
        _local.conn = conn
    return conn

# ── SQL 方言转换（PostgreSQL → SQLite）──────────────────────────────
def _normalize_sql(sql: str) -> str:
    sql = sql.replace('%s', '?')
    sql = _re.sub(r'\bNOW\s*\(\)', "datetime('now')", sql, flags=_re.IGNORECASE)
    sql = _re.sub(r'\bCURRENT_TIMESTAMP\b', "datetime('now')", sql, flags=_re.IGNORECASE)
    sql = _re.sub(
        r"DATE_TRUNC\s*\(\s*'month'\s*,\s*CURRENT_DATE\s*\)",
        "date('now','start of month')",
        sql, flags=_re.IGNORECASE
    )
    sql = _re.sub(r'\bILIKE\b', 'LIKE', sql, flags=_re.IGNORECASE)
    sql = _re.sub(r'\btrue\b', '1', sql, flags=_re.IGNORECASE)
    sql = _re.sub(r'\bfalse\b', '0', sql, flags=_re.IGNORECASE)
    return sql

# ── 数据类型转换 ─────────────────────────────────────────────────────
def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (datetime, date)):
        return obj
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    return obj

def serialize_params(params):
    if params is None:
        return None
    if isinstance(params, (list, tuple)):
        return tuple(convert_numpy_types(p) for p in params)
    return convert_numpy_types(params)


class _CompatCursor:
    """兼容旧 psycopg2 风格调用的轻量游标包装器"""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        sql = _normalize_sql(query)
        clean_params = serialize_params(params)
        if clean_params is not None:
            self._cursor.execute(
                sql,
                clean_params if isinstance(clean_params, tuple) else (clean_params,)
            )
        else:
            self._cursor.execute(sql)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _CompatConnection:
    """兼容旧 psycopg2 风格调用的轻量连接包装器"""

    def __init__(self, conn):
        self._conn = conn
        self.autocommit = True

    def cursor(self):
        return _CompatCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        elif self.autocommit:
            self.commit()
        return False

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db_connection():
    """向旧页面暴露兼容的 DB 连接对象。"""
    return _CompatConnection(_get_conn())

# ── 核心查询函数 ─────────────────────────────────────────────────────
def execute_query(
    query: str,
    params: Optional[Union[List, Tuple, Dict]] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
    commit: bool = False,
) -> Optional[Union[List[Dict], Dict, int]]:
    clean_params = serialize_params(params)
    sql = _normalize_sql(query)
    conn = _get_conn()

    try:
        cur = conn.cursor()
        if clean_params is not None:
            cur.execute(sql, clean_params if isinstance(clean_params, tuple) else (clean_params,))
        else:
            cur.execute(sql)

        if fetch_one:
            row = cur.fetchone()
            result = dict(row) if row else None
        elif fetch_all:
            rows = cur.fetchall()
            result = [dict(r) for r in rows] if rows else []
        else:
            result = cur.rowcount

        if commit:
            conn.commit()
            logger.debug(f"事务已提交，影响行数: {cur.rowcount}")

        return convert_numpy_types(result) if result else result

    except sqlite3.Error as e:
        logger.error(f"数据库错误: {e}")
        logger.error(f"查询: {sql[:120]}")
        logger.error(f"参数: <{len(params) if params else 0} 个值>")
        conn.rollback()
        raise
    except Exception as e:
        logger.error(f"查询异常: {e}")
        conn.rollback()
        raise

def test_connection() -> bool:
    try:
        result = execute_query("SELECT 1 AS test", fetch_one=True)
        return result is not None and result.get('test') == 1
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

def get_table_info(table_name: str) -> List[Dict]:
    try:
        _assert_safe_identifier(table_name, 'table')
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"获取表 {table_name} 信息失败: {e}")
        return []

def check_table_exists(table_name: str) -> bool:
    try:
        result = execute_query(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s",
            params=(table_name,), fetch_one=True
        )
        return result is not None
    except Exception as e:
        logger.error(f"检查表 {table_name} 是否存在失败: {e}")
        return False

# ── 专用查询函数 ─────────────────────────────────────────────────────
def get_all_molds(offset: int = 0, limit: int = 100) -> List[Dict]:
    try:
        query = """
        SELECT
            m.mold_id, m.mold_code, m.mold_name, m.mold_drawing_number,
            mft.type_name  AS functional_type,
            m.supplier, m.manufacturing_date,
            m.theoretical_lifespan_strokes, m.accumulated_strokes,
            m.maintenance_cycle_strokes,
            ms.status_name   AS current_status,
            sl.location_name AS current_location,
            u.full_name      AS responsible_person,
            m.remarks, m.created_at, m.updated_at
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms          ON m.current_status_id        = ms.status_id
        LEFT JOIN storage_locations sl      ON m.current_location_id      = sl.location_id
        LEFT JOIN users u                   ON m.responsible_person_id    = u.user_id
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
        """
        return execute_query(query, params=(limit, offset), fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取模具列表失败: {e}")
        return []

def get_mold_by_id(mold_id: int) -> Optional[Dict]:
    try:
        query = """
        SELECT m.*,
               mft.type_name  AS functional_type,
               ms.status_name   AS current_status,
               sl.location_name AS current_location,
               u.full_name      AS responsible_person
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms          ON m.current_status_id        = ms.status_id
        LEFT JOIN storage_locations sl      ON m.current_location_id      = sl.location_id
        LEFT JOIN users u                   ON m.responsible_person_id    = u.user_id
        WHERE m.mold_id = %s
        """
        return execute_query(query, params=(mold_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"获取模具 {mold_id} 信息失败: {e}")
        return None

def get_loan_statuses() -> List[Dict]:
    try:
        return execute_query(
            "SELECT status_id, status_name, description FROM loan_statuses ORDER BY status_id",
            fetch_all=True
        ) or []
    except Exception as e:
        logger.error(f"获取借用状态失败: {e}")
        return []

def get_mold_statuses() -> List[Dict]:
    try:
        return execute_query(
            "SELECT status_id, status_name, description FROM mold_statuses ORDER BY status_id",
            fetch_all=True
        ) or []
    except Exception as e:
        logger.error(f"获取模具状态失败: {e}")
        return []

def get_storage_locations() -> List[Dict]:
    try:
        return execute_query(
            "SELECT location_id, location_name, description FROM storage_locations ORDER BY location_name",
            fetch_all=True
        ) or []
    except Exception as e:
        logger.error(f"获取存储位置失败: {e}")
        return []

def get_functional_types() -> List[Dict]:
    try:
        return execute_query(
            "SELECT type_id, type_name, description FROM mold_functional_types ORDER BY type_name",
            fetch_all=True
        ) or []
    except Exception as e:
        logger.error(f"获取功能类型失败: {e}")
        return []

# ── 标识符安全白名单 ─────────────────────────────────────────────────
_ALLOWED_TABLES = {
    'molds', 'users', 'roles',
    'mold_loan_records', 'mold_maintenance_logs', 'mold_parts', 'mold_part_categories',
    'system_logs', 'mold_statuses', 'loan_statuses', 'maintenance_result_statuses',
    'maintenance_types', 'mold_functional_types', 'storage_locations',
    'production_equipment', 'production_orders', 'production_schedules',
    'mold_recommendations', 'cost_records', 'products',
}

_IDENTIFIER_RE = _re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _assert_safe_identifier(name: str, kind: str = 'identifier') -> None:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"非法 SQL {kind}：{name!r}")
    if kind == 'table' and name not in _ALLOWED_TABLES:
        raise ValueError(f"表名不在白名单中：{name!r}")

def _get_primary_key(table: str) -> Optional[str]:
    """通过 PRAGMA table_info 读取表的真实主键列名（不靠命名约定猜测）。"""
    for col in get_table_info(table):
        if col.get('pk'):
            return col['name']
    return None

# ── 数据验证函数 ─────────────────────────────────────────────────────
def validate_foreign_key(table: str, column: str, value: Any) -> bool:
    try:
        _assert_safe_identifier(table, 'table')
        _assert_safe_identifier(column, 'column')
        if value is None:
            return True
        result = execute_query(
            f"SELECT 1 FROM {table} WHERE {column} = %s LIMIT 1",
            params=(value,), fetch_one=True
        )
        return result is not None
    except Exception as e:
        logger.error(f"验证外键失败: {table}.{column}={value}, 错误: {e}")
        return False

def validate_unique_constraint(table: str, column: str, value: Any,
                               exclude_id: Optional[int] = None) -> bool:
    try:
        _assert_safe_identifier(table, 'table')
        _assert_safe_identifier(column, 'column')

        query = f"SELECT 1 FROM {table} WHERE {column} = %s"
        params: list = [value]

        if exclude_id is not None:
            primary_key = _get_primary_key(table)
            if not primary_key:
                logger.error(f"无法确定表 {table} 的主键，跳过 exclude_id 过滤")
                raise ValueError(f"表 {table} 无主键，无法按 exclude_id 排除")
            _assert_safe_identifier(primary_key, 'column')
            query += f" AND {primary_key} != %s"
            params.append(exclude_id)

        query += " LIMIT 1"
        result = execute_query(query, params=tuple(params), fetch_one=True)
        return result is None  # 不存在才满足唯一约束
    except Exception as e:
        logger.error(f"验证唯一约束失败: {table}.{column}={value}, 错误: {e}")
        return False

# ── 批量操作函数 ─────────────────────────────────────────────────────
def bulk_insert(table: str, columns: List[str], data: List[List]) -> bool:
    if not data:
        return True
    _assert_safe_identifier(table, 'table')
    for col in columns:
        _assert_safe_identifier(col, 'column')

    conn = _get_conn()
    try:
        placeholders = ', '.join(['?'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        conn.executemany(query, data)
        conn.commit()
        logger.info(f"批量插入成功: {table} — {len(data)} 条")
        return True
    except Exception as e:
        logger.error(f"批量插入失败: {e}")
        conn.rollback()
        return False

def bulk_update(table: str, updates: List[Dict]) -> bool:
    if not updates:
        return True
    _assert_safe_identifier(table, 'table')

    conn = _get_conn()
    try:
        cur = conn.cursor()
        for update in updates:
            if not update.get('set') or not update.get('where'):
                continue
            for col in list(update['set'].keys()) + list(update['where'].keys()):
                _assert_safe_identifier(col, 'column')
            set_clause   = ', '.join([f"{k} = ?" for k in update['set'].keys()])
            where_clause = ' AND '.join([f"{k} = ?" for k in update['where'].keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            params = list(update['set'].values()) + list(update['where'].values())
            cur.execute(query, params)
        conn.commit()
        logger.info(f"批量更新成功: {table} — {len(updates)} 条")
        return True
    except Exception as e:
        logger.error(f"批量更新失败: {e}")
        conn.rollback()
        return False

# ── 事务上下文管理器 ─────────────────────────────────────────────────
@contextmanager
def transaction():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
        logger.debug("事务提交成功")
    except Exception as e:
        conn.rollback()
        logger.error(f"事务回滚: {e}")
        raise

# ── 缓存查找数据 ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_cached_lookup_data():
    try:
        return {
            'mold_statuses':    get_mold_statuses(),
            'loan_statuses':    get_loan_statuses(),
            'storage_locations': get_storage_locations(),
            'functional_types': get_functional_types(),
        }
    except Exception as e:
        logger.error(f"获取缓存查找数据失败: {e}")
        return {}

def clear_cache():
    try:
        st.cache_data.clear()
        logger.info("缓存已清除")
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")

# ── 初始化 ───────────────────────────────────────────────────────────
def initialize_database():
    try:
        _get_conn()  # 确保连接和目录已创建

        init_sql_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'sql', 'sqlite_init.sql'
        )
        if os.path.exists(init_sql_path):
            with open(init_sql_path, encoding='utf-8') as f:
                sql_script = f.read()
            conn = _get_conn()
            conn.executescript(sql_script)
            logger.info("数据库 schema 初始化完成")

            # 兼容历史页面依赖的扩展列（尤其是生产排程模块）
            compat_columns = {
                'production_schedules': {
                    'scheduled_start': "TEXT",
                    'scheduled_end': "TEXT",
                    'actual_start': "TEXT",
                    'actual_end': "TEXT",
                    'operator_id': "INTEGER REFERENCES users(user_id)",
                    'quantity': "INTEGER DEFAULT 0",
                }
            }

            for table_name, columns in compat_columns.items():
                existing_columns = {col['name'] for col in get_table_info(table_name)}
                for column_name, column_def in columns.items():
                    if column_name not in existing_columns:
                        conn.execute(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                        )
                        logger.info(f"已为 {table_name} 补充兼容列: {column_name}")
            conn.commit()
        else:
            logger.warning(f"初始化 SQL 文件不存在: {init_sql_path}")

        if test_connection():
            logger.info(f"SQLite 数据库连接正常: {DB_PATH}")
            return True
        else:
            logger.error("数据库连接测试失败")
            return False
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

initialize_database()
