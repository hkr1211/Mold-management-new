# tests/test_loan_page_entrypoint.py — 借用管理页面入口回归测试
# 验证：未登录访客访问借用页面时，页面调用 st.error 并 st.stop 退出。

import os
import sys
import types
import pytest


class _DummyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def _build_st_mock(session_state: dict) -> types.ModuleType:
    st = types.ModuleType("streamlit")
    st.session_state = session_state
    st._error_calls = []
    st._markdown_calls = []

    st.error = lambda text, **kw: st._error_calls.append(text)
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.warning = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.success = lambda *a, **kw: None
    st.title = lambda *a, **kw: None
    st.markdown = lambda text, **kw: st._markdown_calls.append(text)
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
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
    st.divider = lambda: None
    st.toast = lambda *a, **kw: None
    st.spinner = lambda *a, **kw: _DummyContext()
    st.switch_page = lambda *a, **kw: None
    st.subheader = lambda *a, **kw: None
    st.header = lambda *a, **kw: None
    st.caption = lambda *a, **kw: None
    st.dataframe = lambda *a, **kw: None
    st.metric = lambda *a, **kw: None
    st.write = lambda *a, **kw: None
    st.table = lambda *a, **kw: None
    st.multiselect = lambda label, options, *a, **kw: []
    st.checkbox = lambda *a, **kw: False
    st.radio = lambda label, options, *a, **kw: options[0] if options else None
    st.slider = lambda *a, **kw: 0
    return st


def _load_page(st_mock, extra_modules=None):
    sys.modules["streamlit"] = st_mock

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    # ui mock — inject_global_css / page_header are no-ops
    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.get_db_connection = lambda *a, **kw: None
    database.get_loan_statuses = lambda *a, **kw: []
    database.convert_numpy_types = lambda x: x
    sys.modules["utils.database"] = database

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    nav.nav_buttons = lambda *a, **kw: None
    nav.NAV = {}
    sys.modules["utils.nav"] = nav

    if extra_modules:
        sys.modules.update(extra_modules)

    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "2_借用管理.py"
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    module = types.ModuleType("loan_page")
    exec(compile(src, "2_借用管理.py", "exec"), module.__dict__)
    return module


def test_loan_page_blocks_unauthenticated_user():
    """未登录用户访问借用页时，页面应调用 st.error 后 st.stop 退出。"""
    st = _build_st_mock({"user_role": "访客"})  # logged_in 未设置

    with pytest.raises(SystemExit):
        _load_page(st)

    assert any("登录" in msg for msg in st._error_calls), \
        "未登录时应显示登录提示错误"


def test_loan_page_blocks_unauthorized_role():
    """已登录但角色无权限时，页面应显示权限错误并返回（不崩溃）。"""
    st = _build_st_mock({"logged_in": True, "user_role": "访客"})

    _load_page(st)  # 不应抛异常，直接 return

    assert any("权限" in msg for msg in st._error_calls), \
        "无权限角色应显示权限不足错误"


def test_loan_page_show_is_callable():
    """页面模块定义了 show() 函数。"""
    st = _build_st_mock({"logged_in": True, "user_role": "模具库管理员"})
    module = _load_page(st)
    assert callable(getattr(module, "show", None)), "show() 函数应存在"
