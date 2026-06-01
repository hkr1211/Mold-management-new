# tests/test_loan_schema_compat.py — 借用管理页与当前 SQLite schema 的兼容测试

import os
import re
import sys
import types


def _load_loan_module():
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.title = lambda *a, **kw: None
    st.subheader = lambda *a, **kw: None
    st.warning = lambda *a, **kw: None
    st.error = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.success = lambda *a, **kw: None
    st.metric = lambda *a, **kw: None
    st.write = lambda *a, **kw: None
    st.markdown = lambda *a, **kw: None
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.button = lambda *a, **kw: False
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda n: [_DummyContext() for _ in range(len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.expander = lambda *a, **kw: _DummyContext()
    st.form = lambda *a, **kw: _DummyContext()
    st.rerun = lambda: None
    st.balloons = lambda: None
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    database.get_db_connection = lambda *a, **kw: None
    database.get_loan_statuses = lambda *a, **kw: []
    database.convert_numpy_types = lambda x: x
    sys.modules["utils.database"] = database

    page_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "pages",
        "2_借用管理.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(r'^\s*show\(\)\s*$', "", src, flags=re.MULTILINE)

    module = types.ModuleType("loan_page")
    exec(compile(src, "2_借用管理.py", "exec"), module.__dict__)
    return module


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_loan_list_query_uses_current_sqlite_schema():
    module = _load_loan_module()

    query, params = module._build_loan_list_query(0)

    assert "mlr.application_date AS application_timestamp" in query
    assert "mlr.expected_return_date AS expected_return_timestamp" in query
    assert "mlr.actual_return_date AS actual_return_timestamp" in query
    assert "COALESCE(mlr.purpose, '') as destination_equipment" in query
    assert "application_timestamp" not in query.replace("AS application_timestamp", "")
    assert "expected_return_timestamp" not in query.replace("AS expected_return_timestamp", "")
    assert "actual_return_timestamp" not in query.replace("AS actual_return_timestamp", "")
    assert "approver_id" not in query
    assert params == []


def test_map_legacy_loan_field_to_current_schema():
    module = _load_loan_module()

    assert module._map_legacy_loan_field("actual_return_timestamp") == "actual_return_date"
    assert module._map_legacy_loan_field("approval_timestamp") == "updated_at"
    assert module._map_legacy_loan_field("loan_out_timestamp") == "updated_at"
    assert module._map_legacy_loan_field("approver_id") is None


def test_format_loan_datetime_accepts_string():
    module = _load_loan_module()

    assert module._format_loan_datetime("2026-05-01 10:20:30", "%Y-%m-%d %H:%M") == "2026-05-01 10:20"
