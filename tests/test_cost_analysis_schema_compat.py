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


# 2026-06-11 成本页去假：数据源由无录入口的 cost_records 改为真实的
# mold_maintenance_logs（维修保养记录的费用与起止时间）。

def test_queries_aggregate_real_maintenance_costs():
    module = _load_cost_module()

    for builder in (module._build_cost_summary_query,
                    module._build_cost_trend_query,
                    module._build_cost_composition_query,
                    module._build_downtime_query):
        query = builder()
        assert "mold_maintenance_logs" in query, builder.__name__
        assert "cost_records" not in query, builder.__name__
        assert "DATE_TRUNC" not in query, builder.__name__

    details = module._build_mold_cost_details_query()
    assert "mold_maintenance_logs" in details
    assert "cost_records" not in details


def test_mold_cost_details_query_repair_filter_and_sort_whitelist():
    module = _load_cost_module()

    q_all = module._build_mold_cost_details_query(None, "总费用降序")
    assert "is_repair" not in q_all
    assert "ORDER BY total_cost DESC" in q_all

    q_repair = module._build_mold_cost_details_query(1, "维修次数降序")
    assert "mt.is_repair = %s" in q_repair
    assert "ORDER BY maintenance_count DESC" in q_repair

    # 非法排序输入回落到默认排序（防注入）
    q_bad = module._build_mold_cost_details_query(None, "evil; DROP TABLE molds")
    assert "ORDER BY total_cost DESC" in q_bad
    assert "DROP" not in q_bad


def test_downtime_query_requires_both_timestamps():
    module = _load_cost_module()
    query = module._build_downtime_query()
    assert "maintenance_start_timestamp IS NOT NULL" in query
    assert "maintenance_end_timestamp IS NOT NULL" in query
    assert "julianday" in query


def test_no_hardcoded_demo_numbers_left_in_page():
    """守住"去假"成果：演示数字与假功能不得回归。"""
    page_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pages", "7_成本分析.py")
    with open(page_path, encoding="utf-8") as f:
        src = f.read()
    for fake in ("158000", "235000", "get_optimization_suggestions",
                 "save_cost_targets", "潜在年度节省"):
        assert fake not in src, f"演示数据/假功能回归: {fake}"
