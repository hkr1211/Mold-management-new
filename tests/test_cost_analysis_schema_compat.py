# tests/test_cost_analysis_schema_compat.py — 成本分析页与 SQLite 语法兼容测试

import os
import re
import sys
import types


def _load_cost_module():
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
    st.dataframe = lambda *a, **kw: None
    st.plotly_chart = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.date_input = lambda *a, **kw: None
    st.columns = lambda n: [_DummyContext() for _ in range(len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.button = lambda *a, **kw: False
    st.rerun = lambda: None
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    plotly = types.ModuleType("plotly")
    plotly_graph_objects = types.ModuleType("plotly.graph_objects")
    plotly_express = types.ModuleType("plotly.express")
    sys.modules["plotly"] = plotly
    sys.modules["plotly.graph_objects"] = plotly_graph_objects
    sys.modules["plotly.express"] = plotly_express

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.require_permission = lambda perm: (lambda f: f)
    sys.modules["utils.auth"] = auth

    page_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "pages",
        "7_成本分析.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(r'^\s*show\(\)\s*$', "", src, flags=re.MULTILINE)

    module = types.ModuleType("cost_analysis_page")
    exec(compile(src, "7_成本分析.py", "exec"), module.__dict__)
    return module


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_cost_trend_query_uses_sqlite_grouping():
    module = _load_cost_module()

    query = module._build_cost_trend_query()

    assert "strftime('%Y-%m-%d', record_date) as date" in query
    assert "WHERE record_date BETWEEN %s AND %s" in query
    assert "GROUP BY strftime('%Y-%m-%d', record_date)" in query
    assert "DATE_TRUNC" not in query
    assert "cost_date" not in query


def test_build_cost_composition_query_uses_record_date():
    module = _load_cost_module()

    query = module._build_cost_composition_query()

    assert "FROM cost_records" in query
    assert "WHERE record_date BETWEEN %s AND %s" in query
    assert "GROUP BY cost_type" in query
    assert "cost_date" not in query
