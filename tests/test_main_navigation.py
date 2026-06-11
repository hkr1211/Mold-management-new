# tests/test_main_navigation.py — main.py 导航回归测试
# 验证：_nav_buttons() / _NAV 字典将角色正确映射到页面路径。

import os
import re
import sys
import types
import pytest


class _DummyContext:
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _build_st_mock(clicked_label: str = "") -> types.ModuleType:
    st = types.ModuleType("streamlit")
    st.session_state = {"logged_in": False}
    st._switched_pages = []

    st.set_page_config = lambda **kw: None
    st.markdown = lambda *a, **kw: None
    st.error = lambda *a, **kw: None
    st.warning = lambda *a, **kw: None
    st.success = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.rerun = lambda: None
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    st.divider = lambda: None
    st.spinner = lambda *a, **kw: _DummyContext()
    st.toast = lambda *a, **kw: None
    st.text_input = lambda *a, **kw: ""
    st.columns = lambda n: [_DummyContext() for _ in range(
        len(n) if isinstance(n, (list, tuple)) else n)]
    st.expander = lambda *a, **kw: _DummyContext()
    st.form = lambda *a, **kw: _DummyContext()
    st.form_submit_button = lambda *a, **kw: False
    st.selectbox = lambda label, options, *a, **kw: options[0] if options else None
    st.sidebar = _DummyContext()

    def button(label, **kwargs):
        if label == clicked_label:
            if "switch_page" in kwargs:
                pass
            return True
        return False

    def switch_page(path):
        st._switched_pages.append(path)

    st.button = button
    st.switch_page = switch_page
    return st


def _load_main_module(clicked_label: str = ""):
    st = _build_st_mock(clicked_label)
    sys.modules["streamlit"] = st

    # ui mock
    ui = types.ModuleType("utils.ui")
    ui.inject_global_css = lambda: None
    ui.page_header = lambda *a, **kw: None
    ui.stat_card = lambda *a, **kw: None
    ui.activity_row = lambda *a, **kw: None
    ui.PURPLE = "#7e3af2"
    ui.SUCCESS = "#057a55"
    ui.WARNING = "#c27803"
    ui.DANGER  = "#c81e1e"
    sys.modules["utils.ui"] = ui

    auth = types.ModuleType("utils.auth")
    auth.restore_session = lambda *a, **kw: False
    auth.login_user = lambda *a, **kw: None
    auth.logout_user = lambda *a, **kw: None
    sys.modules["utils.auth"] = auth

    database = types.ModuleType("utils.database")
    database.execute_query = lambda *a, **kw: None
    database.initialize_database = lambda: True
    database.ensure_database_initialized = lambda: True
    database.test_connection = lambda: True
    sys.modules["utils.database"] = database

    # nav mock — 提供 NAV / nav_buttons / setup_sidebar
    _NAV_DATA = {
        '超级管理员': [
            ("🛠️ 模具管理", "pages/1_模具管理.py"),
            ("📋 借用管理", "pages/2_借用管理.py"),
            ("🔧 维修管理", "pages/3_维修管理.py"),
            ("🔩 部件管理", "pages/4_部件管理.py"),
            ("⚙️ 系统管理", "pages/5_系统管理.py"),
            ("🤖 模具推荐", "pages/6_模具推荐.py"),
            ("💰 成本分析", "pages/7_成本分析.py"),
            ("📅 生产排程", "pages/8_生产排程.py"),
        ],
        '模具库管理员': [
            ("🛠️ 模具管理", "pages/1_模具管理.py"),
            ("📋 借用管理", "pages/2_借用管理.py"),
            ("🔧 维修管理", "pages/3_维修管理.py"),
            ("🔩 部件管理", "pages/4_部件管理.py"),
            ("🤖 模具推荐", "pages/6_模具推荐.py"),
            ("💰 成本分析", "pages/7_成本分析.py"),
            ("📅 生产排程", "pages/8_生产排程.py"),
        ],
        '模具工': [
            ("🛠️ 模具管理", "pages/1_模具管理.py"),
            ("🔧 维修管理", "pages/3_维修管理.py"),
            ("🔩 部件管理", "pages/4_部件管理.py"),
        ],
        '冲压操作工': [
            ("🛠️ 模具管理", "pages/1_模具管理.py"),
            ("📝 借用申请", "pages/2_借用管理.py"),
        ],
    }

    def _mock_nav_buttons(role, current_page=""):
        for label, page in _NAV_DATA.get(role, []):
            if st.button(label, use_container_width=True, key=f"nav_{label}"):
                st.switch_page(page)

    nav = types.ModuleType("utils.nav")
    nav.NAV = _NAV_DATA
    nav.nav_buttons = _mock_nav_buttons
    nav.setup_sidebar = lambda *a, **kw: None
    sys.modules["utils.nav"] = nav

    main_path = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")
    with open(main_path, encoding="utf-8") as f:
        src = f.read()

    # 跳过末尾的 main() 调用（避免副作用）
    src = re.sub(r'\nmain\(\)\s*$', '\n', src)

    module = types.ModuleType("main")
    exec(compile(src, "main.py", "exec"), module.__dict__)
    return module, st


# ── 测试 _NAV 字典结构 ─────────────────────────────────────────────────

def test_nav_dict_has_all_four_roles():
    module, _ = _load_main_module()
    nav = module._NAV
    expected = {'超级管理员', '模具库管理员', '模具工', '冲压操作工'}
    assert expected == set(nav.keys())


def test_super_admin_nav_includes_system_management():
    module, _ = _load_main_module()
    pages = [p for _, p in module._NAV['超级管理员']]
    assert "pages/5_系统管理.py" in pages


def test_operator_nav_limited_to_two_modules():
    module, _ = _load_main_module()
    assert len(module._NAV['冲压操作工']) == 2


def test_technician_cannot_access_system_management():
    module, _ = _load_main_module()
    pages = [p for _, p in module._NAV['模具工']]
    assert "pages/5_系统管理.py" not in pages


# ── 测试 _nav_buttons 点击路由 ────────────────────────────────────────

def test_admin_module_nav_routes_to_system_management():
    """超级管理员点击系统管理按钮应跳转到正确页面。"""
    module, st = _load_main_module("⚙️ 系统管理")
    st.session_state = {"logged_in": True, "user_role": "超级管理员",
                        "full_name": "管理员", "username": "admin"}

    module.nav_buttons("超级管理员")

    assert "pages/5_系统管理.py" in st._switched_pages


def test_operator_nav_routes_to_loan_page():
    """冲压操作工点击借用申请应跳转到借用管理页。"""
    module, st = _load_main_module("📝 借用申请")
    st.session_state = {"logged_in": True, "user_role": "冲压操作工",
                        "full_name": "操作工", "username": "op1"}

    module.nav_buttons("冲压操作工")

    assert "pages/2_借用管理.py" in st._switched_pages
