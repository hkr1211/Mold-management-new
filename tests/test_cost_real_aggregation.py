# tests/test_cost_real_aggregation.py — 成本页真实聚合回归（真实 schema）
#
# 成本页此前展示硬编码演示数据；现全部聚合自 mold_maintenance_logs。
# 本测试在 sqlite_init.sql 内存库上插入维修记录，验证各查询算得出正确数字。

import os
import re
import sqlite3
import sys
import types

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")
_PAGE = os.path.join(_HERE, "..", "app", "pages", "7_成本分析.py")


def _real_schema_db():
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row
    return conn


def _load_builders():
    """加载成本页模块（剥离末尾 show()），取 SQL 构建函数。"""
    st = types.ModuleType("streamlit")
    st.session_state = {}
    for name in ("error", "warning", "info", "success", "markdown",
                 "subheader", "metric", "caption", "write"):
        setattr(st, name, lambda *a, **kw: None)
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    plotly_express = types.ModuleType("plotly.express")
    sys.modules["plotly.express"] = plotly_express

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.require_permission = lambda perm: (lambda f: f)
    sys.modules["utils.auth"] = auth

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    ui.download_csv_button = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    with open(_PAGE, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"^show\(\)\s*$", "", src, flags=re.MULTILINE)

    module = types.ModuleType("cost_page")
    exec(compile(src, "7_成本分析.py", "exec"), module.__dict__)
    return module


def _sql(query):
    """页面 SQL 用 %s 占位（运行时由 _normalize_sql 翻译），测试直接转 ?"""
    return query.replace("%s", "?")


def _seed(conn):
    conn.execute("INSERT INTO molds (mold_id, mold_code, mold_name) VALUES (1,'M1','模具一')")
    conn.execute("INSERT INTO molds (mold_id, mold_code, mold_name) VALUES (2,'M2','模具二')")
    # 使用 init 脚本种子数据中的真实类型 id（type_name 唯一）
    repair_id = conn.execute(
        "SELECT type_id FROM maintenance_types WHERE type_name='故障维修'").fetchone()[0]
    upkeep_id = conn.execute(
        "SELECT type_id FROM maintenance_types WHERE type_name='定期保养'").fetchone()[0]
    # 范围内：M1 两条（维修 500 + 保养 200，各 2 小时/4 小时），M2 一条（维修 300）
    rows = [
        (1, repair_id, 500, '2026-06-01 08:00:00', '2026-06-01 10:00:00'),
        (1, upkeep_id, 200, '2026-06-02 08:00:00', '2026-06-02 12:00:00'),
        (2, repair_id, 300, '2026-06-03 08:00:00', '2026-06-03 09:30:00'),
        # 范围外的一条，不应被计入
        (2, repair_id, 9999, '2026-01-01 08:00:00', '2026-01-01 09:00:00'),
    ]
    conn.executemany(
        "INSERT INTO mold_maintenance_logs (mold_id, maintenance_type_id, cost, "
        "maintenance_start_timestamp, maintenance_end_timestamp) VALUES (?,?,?,?,?)",
        rows)
    conn.commit()


def test_summary_trend_composition_details_downtime():
    conn = _real_schema_db()
    _seed(conn)
    m = _load_builders()
    rng = ("2026-06-01", "2026-06-30")

    # 汇总：1000 元 / 3 次 / 2 个模具（范围外 9999 不计）
    row = conn.execute(_sql(m._build_cost_summary_query()), rng).fetchone()
    assert row["total_cost"] == 1000
    assert row["maintenance_count"] == 3
    assert row["mold_count"] == 2

    # 趋势：三天各一条
    trend = conn.execute(_sql(m._build_cost_trend_query()), rng).fetchall()
    assert [(r["date"], r["total_cost"]) for r in trend] == [
        ("2026-06-01", 500), ("2026-06-02", 200), ("2026-06-03", 300)]

    # 构成：按类型聚合
    comp = {r["cost_type"]: r["total_amount"]
            for r in conn.execute(_sql(m._build_cost_composition_query()), rng)}
    assert comp == {"故障维修": 800, "定期保养": 200}

    # 模具明细：默认总费用降序；仅维修过滤
    details = conn.execute(
        _sql(m._build_mold_cost_details_query()), rng + (10,)).fetchall()
    assert [(r["mold_code"], r["total_cost"]) for r in details] == [("M1", 700), ("M2", 300)]

    repair_only = conn.execute(
        _sql(m._build_mold_cost_details_query(1, "总费用降序")), rng + (1, 10)).fetchall()
    assert [(r["mold_code"], r["total_cost"]) for r in repair_only] == [("M1", 500), ("M2", 300)]

    # 停机：2h + 4h + 1.5h
    downtime = conn.execute(_sql(m._build_downtime_query()), rng).fetchall()
    hours = sorted(round(r["hours"], 1) for r in downtime)
    assert hours == [1.5, 2.0, 4.0]
