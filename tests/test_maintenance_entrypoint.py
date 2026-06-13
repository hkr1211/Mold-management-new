# tests/test_maintenance_entrypoint.py — 维修管理页面入口回归测试
# 验证：访问控制守卫生效；授权用户空数据下加载不崩、不误报失败。

import os
import sys
import types
import datetime as _dt
import pytest


class _DummyContext:
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
                 "plotly_chart", "progress", "divider", "download_button",
                 "exception", "table", "spinner", "code"):
        setattr(st, name, lambda *a, **kw: None)
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: _dt.date.today()
    st.time_input = lambda *a, **kw: _dt.time(8, 0)
    st.slider = lambda *a, **kw: 0
    st.selectbox = lambda label, options, *a, **kw: (options[0] if options else None)
    st.multiselect = lambda label, options, *a, **kw: []
    st.checkbox = lambda *a, **kw: False
    st.radio = lambda label, options, *a, **kw: (options[0] if options else None)
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
    st.spinner = lambda *a, **kw: _DummyContext(st)
    st.column_config = types.SimpleNamespace(
        NumberColumn=lambda *a, **kw: None,
        TextColumn=lambda *a, **kw: None,
    )
    return st


def _load_page(st_mock):
    sys.modules["streamlit"] = st_mock

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    # 清除其它测试残留的 plotly mock 占位，强制真实导入
    for _m in ("plotly.graph_objects", "plotly.express", "plotly"):
        _mod = sys.modules.get(_m)
        if _mod is not None and not getattr(_mod, "__file__", None):
            del sys.modules[_m]
    import plotly.graph_objects as go
    import plotly.express as px
    sys.modules["plotly.graph_objects"] = go
    sys.modules["plotly.express"] = px

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    ui.download_csv_button = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.get_db_connection = lambda *a, **kw: None
    database.get_mold_by_id = lambda *a, **kw: None
    database.get_all_molds = lambda *a, **kw: []
    database.convert_numpy_types = lambda x: x
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.restore_session = lambda *a, **kw: False
    auth.has_permission = lambda *a, **kw: True
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "3_维修管理.py"
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    module = types.ModuleType("maint_page")
    exec(compile(src, "3_维修管理.py", "exec"), module.__dict__)
    return module


def test_blocks_unauthenticated_user():
    st = _build_st_mock({})
    with pytest.raises(SystemExit):
        _load_page(st)
    assert any("登录" in msg for msg in st._error_calls)


def test_blocks_unauthorized_role():
    st = _build_st_mock({"logged_in": True, "user_role": "访客"})
    _load_page(st)  # 越权角色 st.error 后 return（不 st.stop）
    assert any("权限" in msg for msg in st._error_calls)


def test_authorized_load_with_empty_data_does_not_crash():
    st = _build_st_mock({"logged_in": True, "user_role": "超级管理员"})
    _load_page(st)  # 顶层 show()：默认 5 个 tab 在空数据下渲染不应抛异常
    assert all("失败" not in msg for msg in st._error_calls)
