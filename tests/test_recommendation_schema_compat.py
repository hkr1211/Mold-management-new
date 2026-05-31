# tests/test_recommendation_schema_compat.py — 模具推荐页与当前 SQLite schema 的兼容测试

import os
import re
import sys
import types


def _load_recommendation_module():
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
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 0
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.button = lambda *a, **kw: False
    st.columns = lambda n: [_DummyContext() for _ in range(len(n) if isinstance(n, (list, tuple)) else n)]
    st.tabs = lambda labels: [_DummyContext() for _ in labels]
    st.expander = lambda *a, **kw: _DummyContext()
    st.rerun = lambda: None
    st.balloons = lambda: None
    sys.modules["streamlit"] = st

    import numpy as np
    import pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd

    plotly = types.ModuleType("plotly")
    plotly_graph_objects = types.ModuleType("plotly.graph_objects")
    plotly_graph_objects.Figure = lambda *a, **kw: _DummyFigure()
    plotly_graph_objects.Scatterpolar = lambda *a, **kw: {"args": a, "kwargs": kw}
    sys.modules["plotly"] = plotly
    sys.modules["plotly.graph_objects"] = plotly_graph_objects

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
        "6_模具推荐.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(r'^\s*show\(\)\s*$', "", src, flags=re.MULTILINE)

    module = types.ModuleType("recommendation_page")
    exec(compile(src, "6_模具推荐.py", "exec"), module.__dict__)
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


def test_build_recommendation_history_query_uses_current_sqlite_schema():
    module = _load_recommendation_module()

    query = module._build_recommendation_history_query()

    assert "mr.score AS recommendation_score" in query
    assert "mr.reason AS recommendation_reason" in query
    assert "'' AS order_code" in query
    assert "0 AS is_selected" in query
    assert "LEFT JOIN products p ON mr.product_id = p.product_id" in query
    assert "LEFT JOIN molds m ON mr.mold_id = m.mold_id" in query
    assert "mr.recommendation_score" not in query
    assert "mr.recommendation_reason" not in query
    assert "mr.order_id" not in query


def test_build_save_recommendation_insert_query_uses_current_sqlite_schema():
    module = _load_recommendation_module()

    query = module._build_save_recommendation_insert_query()

    assert "INSERT INTO mold_recommendations" in query
    assert "(mold_id, product_id, score, reason, created_at)" in query
    assert "VALUES (%s, %s, %s, %s, %s)" in query
    assert "order_id" not in query
    assert "is_selected" not in query
