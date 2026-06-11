# tests/test_master_data.py — 主数据维护 CRUD 回归（真实 schema）
#
# P0 第 5 项：存放位置/部件类别/维修类型/功能类型此前只能手写 SQL 维护。
# 本测试在 sqlite_init.sql 内存库上验证新增/编辑/引用保护删除的完整语义。

import os
import re
import sqlite3
import sys
import types

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")
_PAGE = os.path.join(_HERE, "..", "app", "pages", "5_系统管理.py")


class _DummyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def _load_module():
    """加载系统管理页模块（剥离末尾 show()）。"""
    st = types.ModuleType("streamlit")
    st.session_state = {}
    for name in ("error", "warning", "info", "success", "markdown", "subheader",
                 "caption", "metric", "write", "dataframe", "header", "title"):
        setattr(st, name, lambda *a, **kw: None)
    st.text_input = lambda *a, **kw: ""
    st.selectbox = lambda label, options, *a, **kw: (list(options)[0] if options else None)
    st.checkbox = lambda *a, **kw: False
    st.button = lambda *a, **kw: False
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda n: [_DummyContext() for _ in range(
        len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.expander = lambda *a, **kw: _DummyContext()
    st.form = lambda *a, **kw: _DummyContext()
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.rerun = lambda: None
    st.stop = lambda: None
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    for mod_name in ("plotly", "plotly.graph_objects", "plotly.express"):
        sys.modules[mod_name] = types.ModuleType(mod_name)

    psutil = types.ModuleType("psutil")
    psutil.boot_time = lambda: 0
    sys.modules["psutil"] = psutil

    auth = types.ModuleType("utils.auth")
    for fn in ("has_permission", "get_all_users", "create_user", "update_user_status",
               "update_user", "get_user_activity_log", "get_all_roles",
               "validate_password_strength", "update_user_password", "log_user_action"):
        setattr(auth, fn, lambda *a, **kw: (True, "ok"))
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.test_connection = lambda: True
    sys.modules["utils.database"] = database

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    with open(_PAGE, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"^show\(\)\s*$", "", src, flags=re.MULTILINE)

    module = types.ModuleType("sysmgmt_master")
    exec(compile(src, "5_系统管理.py", "exec"), module.__dict__)
    return module


def _wire_real_db(module):
    """把模块的 execute_query 接到真实 schema 的内存库上。"""
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row

    def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        cur = conn.execute(query.replace("%s", "?"), params or ())
        if fetch_one:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch_all:
            return [dict(r) for r in cur.fetchall()]
        if commit:
            conn.commit()
        return cur.rowcount

    module.execute_query = execute_query
    return conn


def test_insert_list_update_roundtrip():
    m = _load_module()
    conn = _wire_real_db(m)
    cfg = m._MASTER_TABLES["存放位置"]

    ok, msg = m._master_insert(cfg, "  A区货架  ", "一号车间")
    assert ok and "A区货架" in msg

    rows = m._master_list(cfg)
    target = next(r for r in rows if r["name"] == "A区货架")  # 名称已去空白
    assert target["description"] == "一号车间"

    # 重名拒绝（UNIQUE 友好提示）
    ok, msg = m._master_insert(cfg, "A区货架")
    assert not ok and "已存在" in msg

    # 空名拒绝
    ok, _ = m._master_insert(cfg, "   ")
    assert not ok

    # 编辑改名
    ok, _ = m._master_update(cfg, target["id"], "A区货架(停用)", "已搬迁")
    assert ok
    updated = next(r for r in m._master_list(cfg) if r["id"] == target["id"])
    assert updated["name"] == "A区货架(停用)"
    assert updated["description"] == "已搬迁"


def test_maintenance_type_is_repair_flag():
    m = _load_module()
    _wire_real_db(m)
    cfg = m._MASTER_TABLES["维修类型"]

    ok, _ = m._master_insert(cfg, "压边圈更换", "更换磨损压边圈", is_repair=True)
    assert ok
    row = next(r for r in m._master_list(cfg) if r["name"] == "压边圈更换")
    assert row["is_repair"] == 1

    ok, _ = m._master_update(cfg, row["id"], "压边圈更换", None, is_repair=False)
    assert ok
    row = next(r for r in m._master_list(cfg) if r["id"] == row["id"])
    assert row["is_repair"] == 0


def test_delete_blocked_when_referenced():
    m = _load_module()
    conn = _wire_real_db(m)
    cfg = m._MASTER_TABLES["存放位置"]

    ok, _ = m._master_insert(cfg, "B区")
    assert ok
    loc_id = next(r["id"] for r in m._master_list(cfg) if r["name"] == "B区")

    # 模具引用该位置 → 删除被拒
    conn.execute(
        "INSERT INTO molds (mold_code, mold_name, current_location_id) VALUES ('M1','模具一',?)",
        (loc_id,))
    conn.commit()
    assert m._master_ref_count(cfg, loc_id) == 1
    ok, msg = m._master_delete(cfg, loc_id)
    assert not ok and "引用" in msg

    # 解除引用后可删
    conn.execute("UPDATE molds SET current_location_id = NULL")
    conn.commit()
    ok, _ = m._master_delete(cfg, loc_id)
    assert ok
    assert all(r["name"] != "B区" for r in m._master_list(cfg))


def test_all_master_tables_configs_valid():
    """四张字典表的配置均能在真实 schema 上列表/新增。"""
    m = _load_module()
    _wire_real_db(m)
    for label, cfg in m._MASTER_TABLES.items():
        m._master_list(cfg)  # 不抛异常
        ok, msg = m._master_insert(cfg, f"测试-{label}")
        assert ok, f"{label}: {msg}"
