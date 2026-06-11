# tests/test_session_persistence.py — 登录会话持久化回归（真实 schema）
#
# P1 第 1 项：此前登录态只存 st.session_state，刷新页面即掉线。
# 现登录生成服务端令牌（user_sessions 表）经 URL 参数 sid 携带，
# 刷新后 restore_session() 恢复登录态；登出吊销、到期失效。

import os
import sqlite3
import sys
import types

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")
_AUTH = os.path.join(_HERE, "..", "app", "utils", "auth.py")


def _build_env():
    """加载 auth 模块：streamlit mock（含 query_params）+ 真实 schema 内存库。"""
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.query_params = {}
    for name in ("error", "warning", "info", "success", "stop"):
        setattr(st, name, lambda *a, **kw: None)
    sys.modules["streamlit"] = st

    bcrypt = types.ModuleType("bcrypt")
    bcrypt.checkpw = lambda p, h: p == h
    bcrypt.hashpw = lambda p, s: p
    bcrypt.gensalt = lambda: b"salt"
    sys.modules["bcrypt"] = bcrypt

    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row

    def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        q = query.replace("%s", "?").replace("= true", "= 1")
        cur = conn.execute(q, params or ())
        if fetch_one:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch_all:
            return [dict(r) for r in cur.fetchall()]
        if commit:
            conn.commit()
        return cur.rowcount

    database = types.ModuleType("utils.database")
    database.execute_query = execute_query
    database.check_table_exists = lambda name: True
    sys.modules["utils.database"] = database

    with open(_AUTH, encoding="utf-8") as f:
        src = f.read()
    module = types.ModuleType("auth_mod")
    exec(compile(src, "auth.py", "exec"), module.__dict__)

    # 准备一个在职用户
    conn.execute(
        "INSERT INTO users (user_id, username, password_hash, full_name, role_id, is_active) "
        "VALUES (501, 'tester', 'x', '测试员', "
        "(SELECT role_id FROM roles WHERE role_name='模具工'), 1)")
    conn.commit()
    return module, st, conn


def test_create_restore_roundtrip():
    auth, st, _ = _build_env()

    token = auth.create_session(501)
    assert token

    # 模拟刷新：session_state 清空，仅 URL 带令牌
    st.session_state.clear()
    st.query_params["sid"] = token
    assert auth.restore_session() is True
    assert st.session_state["logged_in"] is True
    assert st.session_state["user_id"] == 501
    assert st.session_state["username"] == "tester"
    assert st.session_state["user_role"] == "模具工"
    assert st.session_state["session_token"] == token


def test_invalid_token_rejected_and_cleaned():
    auth, st, _ = _build_env()
    st.query_params["sid"] = "no-such-token"
    assert auth.restore_session() is False
    assert "sid" not in st.query_params  # 失效令牌从 URL 清掉
    assert not st.session_state.get("logged_in")


def test_expired_token_rejected():
    auth, st, conn = _build_env()
    conn.execute(
        "INSERT INTO user_sessions (session_token, user_id, expires_at) "
        "VALUES ('expired-token', 501, datetime('now', '-1 day'))")
    conn.commit()
    st.query_params["sid"] = "expired-token"
    assert auth.restore_session() is False


def test_inactive_user_rejected():
    auth, st, conn = _build_env()
    token = auth.create_session(501)
    conn.execute("UPDATE users SET is_active = 0 WHERE user_id = 501")
    conn.commit()
    st.session_state.clear()
    st.query_params["sid"] = token
    assert auth.restore_session() is False  # 停用账号的令牌立即失效


def test_logout_revokes_token():
    auth, st, _ = _build_env()
    token = auth.create_session(501)
    st.session_state.update({"logged_in": True, "username": "tester",
                             "user_id": 501, "session_token": token})
    st.query_params["sid"] = token

    auth.logout_user()
    assert "sid" not in st.query_params
    assert not st.session_state  # 会话已清空

    # 吊销后令牌不可再恢复
    st.query_params["sid"] = token
    assert auth.restore_session() is False
