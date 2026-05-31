# tests/test_part_management_entrypoint.py — 部件管理页面入口回归测试
# 验证：访问控制守卫正常；授权用户在空数据下加载页面不崩溃（错误处理改造后）。

import os
import sys
import types
import pytest


class _DummyContext:
    """容器上下文：未知属性（如 c1.text_input）代理到 st mock，模拟列/标签页作用域。"""
    def __init__(self, st):
        self._st = st
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def __getattr__(self, name):
        return getattr(self._st, name)


def _build_st_mock(session_state: dict) -> types.ModuleType:
    st = types.ModuleType("streamlit")
    st.session_state = session_state
    st._error_calls = []

    st.error = lambda text, **kw: st._error_calls.append(text)
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.warning = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.success = lambda *a, **kw: None
    st.markdown = lambda *a, **kw: None
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.button = lambda *a, **kw: False
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda n: [_DummyContext(st) for _ in range(
        len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext(st) for _ in labels]
    st.expander = lambda *a, **kw: _DummyContext(st)
    st.form = lambda *a, **kw: _DummyContext(st)
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.rerun = lambda: None
    st.divider = lambda: None
    st.subheader = lambda *a, **kw: None
    st.caption = lambda *a, **kw: None
    st.dataframe = lambda *a, **kw: None
    st.metric = lambda *a, **kw: None
    st.code = lambda *a, **kw: None
    return st


def _load_page(st_mock):
    sys.modules["streamlit"] = st_mock

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.has_permission = lambda *a, **kw: True
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "4_部件管理.py"
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    module = types.ModuleType("part_page")
    exec(compile(src, "4_部件管理.py", "exec"), module.__dict__)
    return module


def test_blocks_unauthenticated_user():
    """未登录用户应被 st.error + st.stop 拦截。"""
    st = _build_st_mock({"user_role": "访客"})
    with pytest.raises(SystemExit):
        _load_page(st)
    assert any("登录" in msg for msg in st._error_calls)


def test_blocks_unauthorized_role():
    """已登录但角色不在白名单时应被权限错误 + st.stop 拦截。"""
    st = _build_st_mock({"logged_in": True, "user_role": "冲压操作工"})
    with pytest.raises(SystemExit):
        _load_page(st)
    assert any("权限" in msg for msg in st._error_calls)


def test_authorized_load_with_empty_data_does_not_crash():
    """授权用户在空数据下加载页面不应崩溃（错误处理改造后回归）。"""
    st = _build_st_mock({"logged_in": True, "user_role": "超级管理员"})
    module = _load_page(st)  # 顶层会执行 show()，不应抛异常
    assert callable(getattr(module, "show", None))
