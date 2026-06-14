# tests/test_mold_row_actions.py — 模具列表行内"编辑/借用/维修"按钮接线回归
#
# 验证点击行内按钮后：编辑→载入 edit_mold_code（同页标签）；
# 借用→preselect_loan_mold_id + 跳转借用页；维修→create_maintenance_mold_id
# + maintenance_tab + 跳转维修页。

import os
import sys
import types
import pytest

_PAGE = os.path.join(os.path.dirname(__file__), "..", "app", "pages", "1_模具管理.py")

# 单行模具数据（含列表/编辑/履历各处用到的键）
_MOLD = {
    "mold_id": 7, "模具编号": "MD-007", "模具名称": "测试模具",
    "功能类型": "拉延", "当前状态": "闲置", "存放位置": "A库",
    "累计模次": 1000, "理论寿命": 500000, "保养周期": 50000,
    "负责人": "张三", "制作人": "李四", "模具规格": "100x100",
    "mold_code": "MD-007", "mold_name": "测试模具", "accumulated_strokes": 1000,
}


class _Ctx:
    def __init__(self, st): self._st = st
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, n): return getattr(self._st, n)


def _load(true_button_key, extra_state=None):
    """加载模具页，让 key==true_button_key 的按钮返回 True，捕获 switch_page。"""
    st = types.ModuleType("streamlit")
    st.session_state = {"logged_in": True, "user_role": "超级管理员", "user_id": 1}
    if extra_state:
        st.session_state.update(extra_state)
    st._switched = []
    st._reran = []
    st._forms = []

    for n in ("error", "warning", "info", "success", "markdown", "plotly_chart",
              "progress", "divider", "metric", "subheader", "caption", "dataframe",
              "write", "code", "balloons"):
        setattr(st, n, lambda *a, **kw: None)
    st.text_input = lambda *a, **kw: ""
    st.number_input = lambda *a, **kw: 1
    st.text_area = lambda *a, **kw: ""
    st.date_input = lambda *a, **kw: None
    st.selectbox = lambda label, options, *a, **kw: (list(options)[0] if options else None)
    st.button = lambda *a, **kw: (kw.get("key") == true_button_key)
    st.form_submit_button = lambda *a, **kw: False
    st.columns = lambda spec: [_Ctx(st) for _ in range(
        len(spec) if isinstance(spec, (list, tuple)) else spec)]
    st.tabs = lambda labels: [_Ctx(st) for _ in labels]
    st.expander = lambda *a, **kw: _Ctx(st)
    st.container = lambda *a, **kw: _Ctx(st)
    st.form = lambda *a, **kw: (st._forms.append(a[0] if a else kw.get("key")), _Ctx(st))[1]
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.rerun = lambda: st._reran.append(True)
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.switch_page = lambda p: st._switched.append(p)
    sys.modules["streamlit"] = st

    import numpy as np, pandas as pd
    sys.modules["numpy"] = np
    sys.modules["pandas"] = pd
    for m in ("plotly.graph_objects", "plotly.express", "plotly"):
        mod = sys.modules.get(m)
        if mod is not None and not getattr(mod, "__file__", None):
            del sys.modules[m]
    import plotly.express as px
    sys.modules["plotly.express"] = px

    def eq(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        q = query or ""
        if "full_name FROM users" in q:  # load_lookup_data 的用户下拉
            return [{"user_id": 1, "full_name": "张三"}]
        if "FROM mold_stroke_logs" in q:  # 履历模次流水
            return []
        if "AS s" in q:  # _last_maintenance_strokes
            return {"s": 0}
        if fetch_one:
            return dict(_MOLD)
        if fetch_all:
            return [dict(_MOLD)]
        return 0

    database = types.ModuleType("utils.database")
    database.execute_query = eq
    database.get_all_molds = lambda *a, **kw: [dict(_MOLD)]
    database.get_mold_statuses = lambda *a, **kw: [{"status_id": 1, "status_name": "闲置"}]
    database.get_storage_locations = lambda *a, **kw: []
    database.get_functional_types = lambda *a, **kw: []
    sys.modules["utils.database"] = database

    auth = types.ModuleType("utils.auth")
    auth.restore_session = lambda *a, **kw: False
    auth.has_permission = lambda *a, **kw: True
    auth.log_user_action = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    ui.download_csv_button = lambda *a, **kw: None
    ui.render_qr_label = lambda *a, **kw: None
    sys.modules["utils.ui"] = ui

    nav = types.ModuleType("utils.nav")
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    with open(_PAGE, encoding="utf-8") as f:
        src = f.read()
    module = types.ModuleType("mold_page_actions")
    try:
        exec(compile(src, "1_模具管理.py", "exec"), module.__dict__)
    except SystemExit:
        pass
    return st


def test_edit_button_sets_edit_code():
    st = _load("edit_7")
    assert st.session_state.get("edit_mold_code") == "MD-007"
    assert st._reran  # 触发 rerun（同页切到编辑标签）


def test_loan_button_preselects_and_navigates():
    st = _load("loan_7")
    assert st.session_state.get("preselect_loan_mold_id") == 7
    assert any("2_" in p for p in st._switched)  # 跳转借用页


def test_maintenance_button_preselects_and_navigates():
    st = _load("maint_7")
    assert st.session_state.get("create_maintenance_mold_id") == 7
    assert st.session_state.get("maintenance_tab") == "create_task"
    assert any("3_" in p for p in st._switched)  # 跳转维修页


def test_edit_code_set_renders_inline_editor():
    """预设 edit_mold_code（模拟点击编辑后）应在列表页就地展开编辑表单，无需切标签。"""
    st = _load("none", extra_state={"edit_mold_code": "MD-007"})
    assert "inline_mold_form" in st._forms  # 行内编辑表单已渲染
