# tests/test_schedule_schema_compat.py — 生产排程页兼容测试

import os
import re
import sys
import types
from datetime import date


def _load_schedule_module():
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
    st.caption = lambda *a, **kw: None
    st.progress = lambda *a, **kw: None
    st.dataframe = lambda *a, **kw: None
    st.plotly_chart = lambda *a, **kw: None
    st.radio = lambda label, options, *a, **kw: options[0] if options else None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.multiselect = lambda label, options, *a, **kw: [options[0]] if options else []
    st.date_input = lambda *a, **kw: date.today()
    st.time_input = lambda *a, **kw: None
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.button = lambda *a, **kw: False
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda n: [_DummyContext() for _ in range(len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.expander = lambda *a, **kw: _DummyContext()
    st.form = lambda *a, **kw: _DummyContext()
    st.spinner = lambda *a, **kw: _DummyContext()
    st.rerun = lambda: None
    st.balloons = lambda: None
    st.column_config = types.SimpleNamespace(NumberColumn=lambda *a, **kw: None)
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    plotly = types.ModuleType("plotly")
    plotly_graph_objects = types.ModuleType("plotly.graph_objects")
    plotly_express = types.ModuleType("plotly.express")
    plotly_graph_objects.Figure = lambda *a, **kw: _DummyFigure()
    plotly_graph_objects.Scatter = lambda *a, **kw: None
    sys.modules["plotly"] = plotly
    sys.modules["plotly.graph_objects"] = plotly_graph_objects
    sys.modules["plotly.express"] = plotly_express

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.require_permission = lambda perm: (lambda f: f)
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    page_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "pages",
        "8_生产排程.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(r'^\s*show\(\)\s*$', "", src, flags=re.MULTILINE)

    module = types.ModuleType("schedule_page")
    exec(compile(src, "8_生产排程.py", "exec"), module.__dict__)
    return module


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyFigure:
    def add_trace(self, *a, **kw):
        return None

    def update_layout(self, *a, **kw):
        return None


def test_schedule_page_has_create_helpers():
    module = _load_schedule_module()

    assert hasattr(module, "get_available_equipment")
    assert hasattr(module, "get_available_operators")
    assert hasattr(module, "get_recommended_molds_for_order")
    assert hasattr(module, "check_schedule_conflicts")
    assert hasattr(module, "create_schedule_record")


def test_build_schedule_data_query_uses_schedule_columns():
    module = _load_schedule_module()

    query = module._build_schedule_data_query()

    assert "ps.scheduled_start" in query
    assert "ps.scheduled_end" in query
    assert "u.full_name as operator_name" in query
    assert "ps.quantity" in query
    assert "DATE(ps.scheduled_start) BETWEEN %s AND %s" in query
