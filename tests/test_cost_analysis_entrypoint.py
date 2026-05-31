# tests/test_cost_analysis_entrypoint.py — 成本分析页面入口回归测试
# 验证：require_permission 守卫生效；授权用户加载页面（含样例数据渲染）不崩、不误报失败。

import os
import sys
import types
import pytest


class _DummyContext:
    """容器上下文：未知属性（如 c1.metric）代理到 st mock。"""
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
    for name in ("warning", "info", "success", "markdown", "subheader",
                 "caption", "dataframe", "write", "metric", "balloons",
                 "plotly_chart", "progress", "divider", "download_button"):
        setattr(st, name, lambda *a, **kw: None)
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.slider = lambda *a, **kw: 0
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
    st.column_config = types.SimpleNamespace(NumberColumn=lambda *a, **kw: None)
    return st


def _make_require_permission(st, has_perm):
    def require_permission(perm):
        def deco(fn):
            def wrapper(*a, **kw):
                if not st.session_state.get('logged_in', False):
                    st.error("🔒 请先登录以访问此页面。")
                    st.stop()
                if not has_perm(perm):
                    st.error("❌ 权限不足")
                    st.stop()
                return fn(*a, **kw)
            return wrapper
        return deco
    return require_permission


def _load_page(st_mock, has_perm=lambda perm: True):
    sys.modules["streamlit"] = st_mock

    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd
    sys.modules["plotly.graph_objects"] = go
    sys.modules["plotly.express"] = px

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.require_permission = _make_require_permission(st_mock, has_perm)
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "7_成本分析.py"
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    module = types.ModuleType("cost_page")
    exec(compile(src, "7_成本分析.py", "exec"), module.__dict__)
    return module


def test_blocks_unauthenticated_user():
    st = _build_st_mock({})
    with pytest.raises(SystemExit):
        _load_page(st)
    assert any("登录" in msg for msg in st._error_calls)


def test_blocks_unauthorized_role():
    st = _build_st_mock({"logged_in": True, "user_role": "冲压操作工"})
    with pytest.raises(SystemExit):
        _load_page(st, has_perm=lambda perm: False)
    assert any("权限" in msg for msg in st._error_calls)


def test_authorized_load_does_not_crash():
    st = _build_st_mock({"logged_in": True, "user_role": "超级管理员"})
    _load_page(st)  # 顶层 show()：4 个 tab（含样例数据图表）渲染不应抛异常
    assert all("失败" not in msg for msg in st._error_calls)
