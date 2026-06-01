# tests/test_auth.py — auth.py 核心逻辑单元测试（无需数据库/Streamlit）

import sys
import types
import os
import pytest

# ── Mock 外部依赖 ─────────────────────────────────────────────────
def _build_mocks():
    # Streamlit mock（session_state 用 dict 模拟）
    st = types.ModuleType('streamlit')
    st.session_state = {}
    st.error = lambda *a, **kw: None
    st.stop = lambda: (_ for _ in ()).throw(SystemExit(0))
    st.cache_data = lambda **kw: (lambda f: f)
    st.cache_data.clear = lambda: None
    sys.modules.setdefault('streamlit', st)

    # bcrypt mock（只需 checkpw / hashpw / gensalt 的签名）
    bcrypt = types.ModuleType('bcrypt')
    bcrypt.checkpw = lambda pwd, hsh: pwd == hsh  # 测试中明文比对
    bcrypt.hashpw = lambda pwd, salt: pwd
    bcrypt.gensalt = lambda: b'$fakesalt'
    sys.modules.setdefault('bcrypt', bcrypt)

    # numpy mock
    import numpy as np
    sys.modules.setdefault('numpy', np)

_build_mocks()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# 用 exec 加载 auth.py，mock 掉 execute_query 和 initialize_database
_auth_src = open(os.path.join(os.path.dirname(__file__), '..', 'app', 'utils', 'auth.py')).read()

_auth_module = types.ModuleType('auth')
_auth_module.__dict__['execute_query'] = lambda *a, **kw: None  # mock DB
exec(compile(_auth_src, 'auth.py', 'exec'), _auth_module.__dict__)

# 便捷引用
_validate = _auth_module.validate_password_strength
_has_perm  = _auth_module.has_permission
_require   = _auth_module.require_permission
_perms     = _auth_module.ROLE_PERMISSIONS
_st        = sys.modules['streamlit']


# ══════════════════════════════════════════════════════════════════
# validate_password_strength
# ══════════════════════════════════════════════════════════════════

class TestValidatePasswordStrength:

    def test_too_short(self):
        ok, msg = _validate("Ab1")
        assert not ok
        assert "位" in msg

    def test_no_uppercase(self):
        ok, msg = _validate("abcdefg1")
        assert not ok
        assert "大写" in msg

    def test_no_lowercase(self):
        ok, msg = _validate("ABCDEFG1")
        assert not ok
        assert "小写" in msg

    def test_no_digit(self):
        ok, msg = _validate("Abcdefgh")
        assert not ok
        assert "数字" in msg

    def test_valid_password(self):
        ok, msg = _validate("Secure123")
        assert ok

    def test_valid_password_complex(self):
        ok, _ = _validate("P@ssw0rd!Extra")
        assert ok

    @pytest.mark.parametrize("pwd", [
        "password123",   # 全小写无大写
        "PASSWORD123",   # 全大写无小写
        "Passwordd",     # 无数字
        "Ab1",           # 太短
    ])
    def test_invalid_passwords(self, pwd):
        ok, _ = _validate(pwd)
        assert not ok


# ══════════════════════════════════════════════════════════════════
# has_permission
# ══════════════════════════════════════════════════════════════════

class TestHasPermission:

    def setup_method(self):
        _st.session_state.clear()

    def test_not_logged_in_returns_false(self):
        assert not _has_perm('view_molds')

    def test_super_admin_has_all(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '超级管理员'
        assert _has_perm('view_molds')
        assert _has_perm('manage_molds')
        assert _has_perm('anything_at_all')

    def test_manager_has_correct_perms(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '模具库管理员'
        assert _has_perm('view_molds')
        assert _has_perm('manage_molds')
        assert _has_perm('approve_loans')
        assert not _has_perm('nonexistent_perm')

    def test_technician_perms(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '模具工'
        assert _has_perm('view_molds')
        assert _has_perm('manage_maintenance')
        assert not _has_perm('manage_molds')
        assert not _has_perm('approve_loans')

    def test_operator_perms(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '冲压操作工'
        assert _has_perm('view_molds')
        assert _has_perm('create_loan')
        assert not _has_perm('manage_molds')
        assert not _has_perm('manage_maintenance')

    def test_unknown_role_has_no_perms(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '访客'
        assert not _has_perm('view_molds')


# ══════════════════════════════════════════════════════════════════
# require_permission 装饰器
# ══════════════════════════════════════════════════════════════════

class TestRequirePermission:

    def setup_method(self):
        _st.session_state.clear()

    def test_not_logged_in_stops(self):
        @_require('view_molds')
        def page():
            return "reached"

        with pytest.raises(SystemExit):
            page()

    def test_insufficient_permission_stops(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '冲压操作工'

        @_require('manage_molds')
        def restricted_page():
            return "reached"

        with pytest.raises(SystemExit):
            restricted_page()

    def test_sufficient_permission_runs(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '模具库管理员'

        @_require('manage_molds')
        def allowed_page():
            return "reached"

        assert allowed_page() == "reached"

    def test_super_admin_always_runs(self):
        _st.session_state['logged_in'] = True
        _st.session_state['user_role'] = '超级管理员'

        @_require('any_permission')
        def admin_page():
            return "ok"

        assert admin_page() == "ok"

    def test_preserves_function_name(self):
        @_require('view_molds')
        def my_named_func():
            pass

        assert my_named_func.__name__ == 'my_named_func'


# ══════════════════════════════════════════════════════════════════
# ROLE_PERMISSIONS 完整性
# ══════════════════════════════════════════════════════════════════

class TestRolePermissions:

    def test_all_roles_defined(self):
        expected_roles = {'超级管理员', '模具库管理员', '模具工', '冲压操作工'}
        assert expected_roles == set(_perms.keys())

    def test_super_admin_wildcard(self):
        assert '*' in _perms['超级管理员']

    def test_view_molds_in_all_roles(self):
        for role, perms in _perms.items():
            if role == '超级管理员':
                continue
            assert 'view_molds' in perms, f"{role} 缺少 view_molds"

    def test_no_duplicate_perms(self):
        for role, perms in _perms.items():
            assert len(perms) == len(set(perms)), f"{role} 有重复权限"


# ══════════════════════════════════════════════════════════════════
# create_user 兼容 role_id / role_name
# ══════════════════════════════════════════════════════════════════

class TestCreateUserCompatibility:

    def test_accepts_role_id_input(self):
        calls = []

        def fake_execute_query(query, params=None, fetch_one=False, commit=False, **kwargs):
            calls.append((query, params, fetch_one, commit))
            if "SELECT user_id FROM users WHERE username" in query:
                return None
            if "SELECT role_id FROM roles WHERE role_id = %s" in query:
                return {"role_id": 3}
            if "INSERT INTO users" in query:
                return 1
            raise AssertionError(f"Unexpected query: {query}")

        _auth_module.execute_query = fake_execute_query

        ok, msg = _auth_module.create_user("zhangsan", "Secure123", "张三", 3, "z@example.com")

        assert ok is True
        assert msg == "用户创建成功"
        assert any("SELECT role_id FROM roles WHERE role_id = %s" in q for q, *_ in calls)

    def test_accepts_role_name_input(self):
        def fake_execute_query(query, params=None, fetch_one=False, commit=False, **kwargs):
            if "SELECT user_id FROM users WHERE username" in query:
                return None
            if "SELECT role_id FROM roles WHERE role_name = %s" in query:
                return {"role_id": 3}
            if "INSERT INTO users" in query:
                return 1
            raise AssertionError(f"Unexpected query: {query}")

        _auth_module.execute_query = fake_execute_query

        ok, msg = _auth_module.create_user("lisi", "Secure123", "李四", "模具工", "l@example.com")

        assert ok is True
        assert msg == "用户创建成功"


# ══════════════════════════════════════════════════════════════════
# 错误处理约定：数据库故障降级，编码缺陷上抛（与 database.py 一致）
# ══════════════════════════════════════════════════════════════════

class TestErrorHandlingContract:
    """auth 数据访问函数只吞 sqlite3.Error，其余异常（编码缺陷）必须上抛。"""

    def teardown_method(self):
        _auth_module.execute_query = lambda *a, **kw: None  # 复位，避免污染其它用例

    def test_db_error_returns_safe_default(self):
        import sqlite3

        def boom(*a, **kw):
            raise sqlite3.OperationalError("database is locked")

        _auth_module.execute_query = boom
        assert _auth_module.get_all_roles() == []  # 降级，不崩

    def test_programming_error_propagates(self):
        def boom(*a, **kw):
            raise ValueError("编码缺陷")

        _auth_module.execute_query = boom
        with pytest.raises(ValueError):
            _auth_module.get_all_roles()  # 不再被吞成 []
