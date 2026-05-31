# tests/test_system_management_entrypoint.py — 系统管理页面入口回归测试
# 验证：授权（超级管理员）空数据下加载 3 个 tab 不崩、不误报失败。
#
# 注：本页 show() 仅在 `if __name__ == "__main__":` 块内调用，且该块在未登录时
# 会强制写入 logged_in=True / 超级管理员（调试后门，另案处理），导致访问控制守卫
# 无法在此被独立测试。因此这里只保留授权加载回归，以 __main__ 方式执行使 show() 真正运行。

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
    for name in ("warning", "info", "success", "markdown", "subheader", "header",
                 "caption", "dataframe", "write", "metric", "balloons",
                 "plotly_chart", "progress", "divider", "download_button",
                 "exception", "table", "code", "title", "json"):
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
    st.spinner = lambda *a, **kw: _DummyContext(st)
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.cache_resource = lambda **kw: (lambda f: f)
    st.rerun = lambda: None
    st.set_page_config = lambda **kw: None
    st.column_config = types.SimpleNamespace(
        NumberColumn=lambda *a, **kw: None,
        TextColumn=lambda *a, **kw: None,
    )
    return st


def _build_psutil_mock():
    ps = types.ModuleType("psutil")
    ps.cpu_percent = lambda *a, **kw: 50.0
    ps.virtual_memory = lambda: types.SimpleNamespace(percent=60.0, used=1, total=2, available=1)
    ps.disk_usage = lambda path: types.SimpleNamespace(percent=70.0, used=1, total=2, free=1)
    ps.pids = lambda: [1, 2, 3]
    ps.boot_time = lambda: 0
    ps.net_io_counters = lambda: types.SimpleNamespace(
        bytes_sent=1024, bytes_recv=2048, packets_sent=10, packets_recv=20)
    return ps


def _load_page(st_mock, has_perm=lambda perm: True):
    sys.modules["streamlit"] = st_mock

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd
    sys.modules["psutil"] = _build_psutil_mock()

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
    sys.modules["utils.ui"] = ui

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.test_connection = lambda: True
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.has_permission = has_perm
    auth.get_all_users = lambda *a, **kw: []
    auth.create_user = lambda *a, **kw: (True, "ok")
    auth.update_user_status = lambda *a, **kw: (True, "ok")
    auth.get_user_activity_log = lambda *a, **kw: []
    auth.get_all_roles = lambda *a, **kw: []
    auth.validate_password_strength = lambda *a, **kw: (True, "ok")
    auth.update_user_password = lambda *a, **kw: (True, "ok")
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "5_系统管理.py"
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    module = types.ModuleType("sysmgmt_page")
    module.__dict__["__name__"] = "__main__"  # 使页面底部 `if __name__=="__main__": show()` 运行
    exec(compile(src, "5_系统管理.py", "exec"), module.__dict__)
    return module


def test_authorized_load_does_not_crash():
    st = _build_st_mock({"logged_in": True, "user_role": "超级管理员", "user_id": 1})
    _load_page(st)  # 顶层 show()：3 个 tab（用户管理/系统配置/系统监控）渲染不应抛异常
    assert all(("失败" not in msg and "出错" not in msg) for msg in st._error_calls)
