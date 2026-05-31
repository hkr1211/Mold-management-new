# tests/test_system_management_user_card.py — 系统管理用户卡片回归测试

import os
import re
import sys
import types
from datetime import datetime


def _build_streamlit_mock():
    st = types.ModuleType("streamlit")
    st.session_state = {"logged_in": True, "user_role": "超级管理员", "user_id": 1}
    st._markdown_calls = []
    st._metrics = []
    st._dataframes = []

    st.set_page_config = lambda **kw: None
    st.title = lambda *a, **kw: None
    st.subheader = lambda *a, **kw: None
    st.header = lambda *a, **kw: None
    st.caption = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.warning = lambda *a, **kw: None
    st.success = lambda *a, **kw: None
    st.error = lambda *a, **kw: None
    st.metric = lambda *a, **kw: st._metrics.append((a, kw))
    st.dataframe = lambda *a, **kw: st._dataframes.append((a, kw))
    st.download_button = lambda *a, **kw: None
    st.rerun = lambda: None
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.cache_resource = lambda **kw: (lambda f: f)
    st.text_input = lambda *a, **kw: ""
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.button = lambda *a, **kw: False
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.columns = lambda n: [_DummyContext() for _ in range(len(n) if isinstance(n, (list, tuple)) else n)]
    st.expander = lambda *a, **kw: _DummyContext()
    st.form = lambda *a, **kw: _DummyContext()
    st.form_submit_button = lambda *a, **kw: False
    st.text_area = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.checkbox = lambda *a, **kw: False
    st.date_input = lambda *a, **kw: datetime.now().date()
    st.markdown = lambda text, **kw: st._markdown_calls.append(text)
    st.column_config = types.SimpleNamespace(
        TextColumn=lambda *a, **kw: {"args": a, "kwargs": kw}
    )
    return st


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _load_system_management_module(logs=None, users=None):
    st = _build_streamlit_mock()
    sys.modules["streamlit"] = st

    plotly = types.ModuleType("plotly")
    plotly_graph_objects = types.ModuleType("plotly.graph_objects")
    plotly_express = types.ModuleType("plotly.express")
    sys.modules["plotly"] = plotly
    sys.modules["plotly.graph_objects"] = plotly_graph_objects
    sys.modules["plotly.express"] = plotly_express

    psutil = types.ModuleType("psutil")
    psutil.boot_time = lambda: 0
    sys.modules["psutil"] = psutil

    import numpy as np
    import pandas as pd

    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    auth = types.ModuleType("utils.auth")
    auth.has_permission = lambda *a, **kw: True
    auth.get_all_users = lambda *a, **kw: users or []
    auth.create_user = lambda *a, **kw: (True, "ok")
    auth.update_user_status = lambda *a, **kw: (True, "ok")
    auth.get_all_roles = lambda *a, **kw: []
    auth.get_user_activity_log = lambda *a, **kw: logs or []
    auth.validate_password_strength = lambda *a, **kw: (True, "ok")
    auth.log_user_action = lambda *a, **kw: None
    auth.update_user_password = lambda *a, **kw: (True, "ok")
    sys.modules["utils.auth"] = auth

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.test_connection = lambda: True
    sys.modules["utils.database"] = database

    page_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "pages",
        "5_系统管理.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(
        r'^\s*show\(\)\s*$',
        "",
        src,
        flags=re.MULTILINE,
    )

    module = types.ModuleType("system_management")
    exec(compile(src, "5_系统管理.py", "exec"), module.__dict__)
    return module, st


def test_display_user_card_accepts_string_created_at():
    module, st = _load_system_management_module()

    module.display_user_card(
        {
            "user_id": 1,
            "username": "admin",
            "full_name": "系统管理员",
            "role_name": "超级管理员",
            "is_active": True,
            "email": "admin@example.com",
            "created_at": "2026-05-01 10:20:30",
        }
    )

    assert any("2026-05-01" in text for text in st._markdown_calls)


def test_show_activity_logs_accepts_string_timestamp():
    module, st = _load_system_management_module(
        logs=[
            {
                "user_id": 1,
                "username": "admin",
                "full_name": "系统管理员",
                "action_type": "LOGIN",
                "target_resource": "system",
                "target_id": "admin",
                "timestamp": "2026-05-01 10:20:30",
            }
        ],
        users=[
            {
                "user_id": 1,
                "username": "admin",
                "full_name": "系统管理员",
            }
        ],
    )

    module.show_activity_logs()

    assert any(args[0] == "今日操作" for args, _ in st._metrics)
    assert len(st._dataframes) == 1


def test_validate_create_user_form_allows_empty_email():
    module, _ = _load_system_management_module(users=[])

    errors, cleaned = module._validate_create_user_form(
        username="zhangsan",
        full_name="张三",
        password="Secure123",
        password_confirm="Secure123",
        email="",
        existing_users=[],
    )

    assert errors == []
    assert cleaned["email"] is None


def test_validate_create_user_form_allows_whitespace_email():
    module, _ = _load_system_management_module(users=[])

    errors, cleaned = module._validate_create_user_form(
        username="zhangsan",
        full_name="张三",
        password="Secure123",
        password_confirm="Secure123",
        email="   ",
        existing_users=[],
    )

    assert errors == []
    assert cleaned["email"] is None


def test_validate_create_user_form_rejects_invalid_non_empty_email():
    module, _ = _load_system_management_module(users=[])

    errors, cleaned = module._validate_create_user_form(
        username="zhangsan",
        full_name="张三",
        password="Secure123",
        password_confirm="Secure123",
        email="abc",
        existing_users=[],
    )

    assert "邮箱格式不正确" in errors
    assert cleaned["email"] == "abc"
