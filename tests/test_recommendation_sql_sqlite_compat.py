# tests/test_recommendation_sql_sqlite_compat.py
# 回归：6_模具推荐.py 的快速查询 / 订单查询此前使用 PostgreSQL 专有 SQL
# （::DECIMAL 强转、不存在的 product_types/materials 表），在 SQLite 下必失败。
# 本测试锁定修复：(1) 页面源码不再含这些 PG 专有用法；
# (2) 修正后的查询能在真实 schema（sqlite_init.sql）的内存库上执行。

import os
import sqlite3
import pytest

_HERE = os.path.dirname(__file__)
_PAGE = os.path.join(_HERE, "..", "app", "pages", "6_模具推荐.py")
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")


def _page_source():
    with open(_PAGE, encoding="utf-8") as f:
        return f.read()


def _memory_db():
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row
    return conn


def test_page_has_no_postgres_specific_sql():
    src = _page_source()
    assert "::DECIMAL" not in src, "残留 PostgreSQL 强制类型转换 ::DECIMAL"
    assert "::" not in src, "残留 PostgreSQL :: 转换语法"
    assert "product_types" not in src, "引用了 schema 中不存在的 product_types 表"
    assert "materials" not in src, "引用了 schema 中不存在的 materials 表"
    assert "material_name" not in src, "引用了不存在的 material_name 列"


# 与页面 show_quick_search() 中查询等价的 SQLite 形式（%s->?, ILIKE->LIKE，
# 由 utils.database._normalize_sql 在运行时完成；此处直接用 SQLite 形式验证语义）。
_QUICK_SEARCH_SQL = """
SELECT
    m.mold_id, m.mold_code, m.mold_name,
    mft.type_name as mold_type,
    ms.status_name as status,
    sl.location_name as location,
    m.theoretical_lifespan_strokes,
    m.accumulated_strokes,
    m.maintenance_cycle_strokes,
    CASE
        WHEN m.theoretical_lifespan_strokes > 0
        THEN ROUND(CAST(m.accumulated_strokes AS REAL) / m.theoretical_lifespan_strokes * 100, 2)
        ELSE 0
    END as usage_percentage
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
WHERE m.mold_code LIKE ? OR m.mold_name LIKE ?
"""

_ORDER_INFO_SQL = """
SELECT
    po.order_id, po.order_code, po.quantity, po.due_date, po.priority,
    p.product_id, p.product_code, p.product_name
FROM production_orders po
JOIN products p ON po.product_id = p.product_id
WHERE po.order_code = ?
"""


def test_quick_search_query_runs_on_real_schema():
    conn = _memory_db()
    rows = conn.execute(_QUICK_SEARCH_SQL, ("%x%", "%x%")).fetchall()  # 不抛异常即通过
    assert rows == []


def test_order_info_query_runs_on_real_schema():
    conn = _memory_db()
    row = conn.execute(_ORDER_INFO_SQL, ("PO-NOT-EXIST",)).fetchone()
    assert row is None
