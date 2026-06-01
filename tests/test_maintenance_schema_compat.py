# tests/test_maintenance_schema_compat.py — 维修管理页与当前 SQLite schema 的兼容测试

import os
import re
import sys
import types


def _load_maintenance_module():
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
    st.checkbox = lambda *a, **kw: False
    st.time_input = lambda *a, **kw: None
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
    database.convert_numpy_types = lambda x: x
    database.get_all_molds = lambda *a, **kw: []
    database.get_mold_by_id = lambda *a, **kw: None
    sys.modules["utils.database"] = database

    page_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "pages",
        "3_维修管理.py",
    )
    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    src = re.sub(r'^\s*show\(\)\s*$', "", src, flags=re.MULTILINE)

    module = types.ModuleType("maintenance_page")
    exec(compile(src, "3_维修管理.py", "exec"), module.__dict__)
    return module


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_maintenance_records_query_uses_current_sqlite_schema():
    module = _load_maintenance_module()

    query, params = module._build_maintenance_records_query(0, 0, "全部")

    assert "mml.description as problem_description" in query
    assert "'' as actions_taken" in query
    assert "mml.cost as maintenance_cost" in query
    assert "'' as notes" in query
    assert "NULL as replaced_parts_info" in query
    assert "JOIN users u ON mml.technician_id = u.user_id" in query
    assert "problem_description" not in query.replace("mml.description as problem_description", "")
    assert "maintained_by_id" not in query
    assert params == []


def test_map_legacy_maintenance_field_to_current_schema():
    module = _load_maintenance_module()

    assert module._map_legacy_maintenance_field("maintained_by_id") == "technician_id"
    assert module._map_legacy_maintenance_field("maintenance_cost") == "cost"
    assert module._map_legacy_maintenance_field("problem_description") == "description"
    assert module._map_legacy_maintenance_field("actions_taken") == "description"
    assert module._map_legacy_maintenance_field("notes") == "description"
    assert module._map_legacy_maintenance_field("replaced_parts_info") is None


def test_format_maintenance_datetime_accepts_string():
    module = _load_maintenance_module()

    assert module._format_maintenance_datetime("2026-05-01 10:20:30", "%Y-%m-%d %H:%M") == "2026-05-01 10:20"


def test_build_maintenance_stats_queries_use_cost_column_and_sqlite_month_grouping():
    module = _load_maintenance_module()

    stats_query, type_stats_query, trend_query = module._build_maintenance_statistics_queries()

    assert "SUM(cost)" in stats_query
    assert "AVG(cost)" in stats_query
    assert "SUM(mml.cost)" in type_stats_query
    assert "AVG(mml.cost)" in type_stats_query
    assert "strftime('%Y-%m-01', mml.maintenance_start_timestamp) as month" in trend_query
    assert "maintenance_cost" not in stats_query
    assert "maintenance_cost" not in type_stats_query
    assert "maintenance_cost" not in trend_query
    assert "DATE_TRUNC" not in trend_query
    assert "INTERVAL '6 months'" not in trend_query
