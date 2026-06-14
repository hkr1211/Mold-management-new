# tests/test_maintenance_parts.py — 维修关联更换部件回归（真实 schema）
#
# P1 第 4 项：维修记录可关联本次更换的已登记部件（maintenance_replaced_parts）。
# 此前是被丢弃的 JSON 自由文本，无法追溯。

import os
import re
import sqlite3
import sys
import types

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")
_PAGE = os.path.join(_HERE, "..", "app", "pages", "3_维修管理.py")


def _load_module():
    st = types.ModuleType("streamlit")
    st.session_state = {}
    for name in ("error", "warning", "info", "success", "markdown", "subheader",
                 "caption", "metric", "write", "dataframe", "code", "balloons"):
        setattr(st, name, lambda *a, **kw: None)
    st.text_input = lambda *a, **kw: ""
    st.text_area = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.date_input = lambda *a, **kw: None
    st.time_input = lambda *a, **kw: None
    st.checkbox = lambda *a, **kw: False
    st.multiselect = lambda label, options, *a, **kw: []
    st.selectbox = lambda label, options, *a, **kw: (list(options)[0] if options else None)
    st.button = lambda *a, **kw: False
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda n: [types.SimpleNamespace(
        __enter__=lambda s: s, __exit__=lambda *a: False) for _ in range(
        len(n) if isinstance(n, (list, tuple)) else n)]
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.rerun = lambda: None
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.get_db_connection = lambda *a, **kw: None
    database.convert_numpy_types = lambda x: x
    database.get_all_molds = lambda *a, **kw: []
    database.get_mold_by_id = lambda *a, **kw: None
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.restore_session = lambda *a, **kw: False
    auth.has_permission = lambda *a, **kw: True
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    ui.download_csv_button = lambda *a, **kw: None
    ui.render_qr_label = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    with open(_PAGE, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"^show\(\)\s*$", "", src, flags=re.MULTILINE)
    module = types.ModuleType("maint_page")
    exec(compile(src, "3_维修管理.py", "exec"), module.__dict__)
    return module


def _wire_real_db(module):
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row

    def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        cur = conn.execute(query.replace("%s", "?"), params or ())
        if fetch_one:
            r = cur.fetchone()
            return dict(r) if r else None
        if fetch_all:
            return [dict(r) for r in cur.fetchall()]
        if commit:
            conn.commit()
        return cur.rowcount

    module.execute_query = execute_query
    return conn


def _seed(conn):
    conn.execute("INSERT INTO molds (mold_id, mold_code, mold_name) VALUES (1,'M1','模具一')")
    cat = conn.execute("SELECT category_id FROM mold_part_categories LIMIT 1").fetchone()[0]
    conn.execute("INSERT INTO mold_parts (part_id, mold_id, part_code, part_name, part_category_id) "
                 "VALUES (10,1,'PC-1','凸模镶块',?)", (cat,))
    conn.execute("INSERT INTO mold_parts (part_id, mold_id, part_code, part_name, part_category_id) "
                 "VALUES (11,1,'PC-2','压边圈',?)", (cat,))
    conn.execute("INSERT INTO mold_maintenance_logs (log_id, mold_id) VALUES (100, 1)")
    conn.commit()


def test_schema_has_link_table():
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "maintenance_replaced_parts" in tables


def test_select_helpers_and_link_roundtrip():
    m = _load_module()
    conn = _wire_real_db(m)
    _seed(conn)

    # 可选部件列表
    opts = m.get_mold_parts_for_select(1)
    assert {o["part_id"] for o in opts} == {10, 11}

    # 关联两个部件到维修记录 100
    for pid in (10, 11):
        m.execute_query("INSERT INTO maintenance_replaced_parts (log_id, part_id, quantity) "
                        "VALUES (%s, %s, 1)", params=(100, pid), commit=True)

    replaced = m.get_replaced_parts(100)
    assert {r["part_name"] for r in replaced} == {"凸模镶块", "压边圈"}
    assert all(r["quantity"] == 1 for r in replaced)

    # 去重用的 id 列表
    ids = {r["part_id"] for r in m.get_replaced_parts_ids(100)}
    assert ids == {10, 11}

    # 另一条无关联的记录返回空
    assert m.get_replaced_parts(999) == []
