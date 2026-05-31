# tests/test_database.py — database.py 核心逻辑单元测试（无需真实数据库）

import sys
import types
import os
import pytest

# ── Mock 外部依赖，使模块可在无数据库环境下导入 ──────────────────
def _build_mocks():
    st = types.ModuleType('streamlit')
    st.cache_data = lambda **kw: (lambda f: f)
    sys.modules.setdefault('streamlit', st)

    import numpy as np
    sys.modules.setdefault('numpy', np)

_build_mocks()

# 修改 sys.path 让 config/settings 可以被找到
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import importlib, re as _re

# 手动加载 database.py（跳过末尾的自动初始化调用）
import re as _re
_src = open(os.path.join(os.path.dirname(__file__), '..', 'app', 'utils', 'database.py')).read()
_src_patched = _re.sub(r'^initialize_database\(\)\s*$', '# initialize_database()',
                       _src, flags=_re.MULTILINE)
# 将 DB_PATH 指向临时内存库，避免在测试环境下创建文件
_src_patched = _src_patched.replace(
    "from config.settings import DB_PATH, CACHE_TTL_SECONDS",
    "DB_PATH = ':memory:'; CACHE_TTL_SECONDS = 300"
)
_db_module = types.ModuleType('database')
exec(compile(_src_patched, 'database.py', 'exec'), _db_module.__dict__)


# ══════════════════════════════════════════════════════════════════
# _assert_safe_identifier — SQL 注入防护
# ══════════════════════════════════════════════════════════════════

class TestAssertSafeIdentifier:
    """_assert_safe_identifier 应拦截所有非法输入，放行合法标识符。"""

    fn = staticmethod(_db_module._assert_safe_identifier)

    # 合法标识符
    @pytest.mark.parametrize("name,kind", [
        ("molds",       "table"),
        ("users",       "table"),
        ("user_id",     "column"),
        ("status_name", "column"),
        ("mold_code",   "column"),
    ])
    def test_valid_identifiers_pass(self, name, kind):
        self.fn(name, kind)  # 不抛异常即为通过

    # 非法格式
    @pytest.mark.parametrize("name,kind", [
        ("1col",                 "column"),   # 数字开头
        ("col name",             "column"),   # 含空格
        ("col-name",             "column"),   # 含连字符
        ("col;DROP TABLE users", "column"),   # SQL 注入
        ("users' OR '1'='1",     "table"),    # 引号注入
    ])
    def test_invalid_format_raises(self, name, kind):
        with pytest.raises(ValueError):
            self.fn(name, kind)

    # 非白名单表名
    @pytest.mark.parametrize("name", [
        "arbitrary_table",
        "pg_shadow",
        "information_schema",
    ])
    def test_non_whitelist_table_raises(self, name):
        with pytest.raises(ValueError):
            self.fn(name, 'table')

    # 列名不受白名单限制（格式合法即可）
    def test_column_not_whitelist_checked(self):
        self.fn('any_valid_column_name', 'column')  # 不应抛异常


# ══════════════════════════════════════════════════════════════════
# convert_numpy_types — 类型转换
# ══════════════════════════════════════════════════════════════════

class TestConvertNumpyTypes:
    fn = staticmethod(_db_module.convert_numpy_types)

    def test_int(self):
        import numpy as np
        assert self.fn(np.int64(42)) == 42
        assert isinstance(self.fn(np.int64(42)), int)

    def test_float(self):
        import numpy as np
        result = self.fn(np.float64(3.14))
        assert abs(result - 3.14) < 1e-9
        assert isinstance(result, float)

    def test_ndarray(self):
        import numpy as np
        result = self.fn(np.array([1, 2, 3]))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_decimal(self):
        from decimal import Decimal
        assert self.fn(Decimal('99.99')) == pytest.approx(99.99)

    def test_dict_recursive(self):
        import numpy as np
        result = self.fn({'a': np.int64(1), 'b': np.float64(2.0)})
        assert result == {'a': 1, 'b': 2.0}

    def test_list_recursive(self):
        import numpy as np
        result = self.fn([np.int64(1), np.int64(2)])
        assert result == [1, 2]

    def test_plain_types_pass_through(self):
        assert self.fn("hello") == "hello"
        assert self.fn(42) == 42
        assert self.fn(None) is None


# ══════════════════════════════════════════════════════════════════
# serialize_params — 参数序列化
# ══════════════════════════════════════════════════════════════════

class TestSerializeParams:
    fn = staticmethod(_db_module.serialize_params)

    def test_none_returns_none(self):
        assert self.fn(None) is None

    def test_tuple_converted(self):
        import numpy as np
        result = self.fn((np.int64(1), 'hello'))
        assert result == (1, 'hello')
        assert isinstance(result[0], int)

    def test_list_converted_to_tuple(self):
        import numpy as np
        result = self.fn([np.float64(1.5)])
        assert isinstance(result, tuple)
        assert result[0] == pytest.approx(1.5)

    def test_scalar_converted(self):
        import numpy as np
        assert self.fn(np.int64(7)) == 7


# ══════════════════════════════════════════════════════════════════
# get_db_connection — 旧页面兼容接口
# ══════════════════════════════════════════════════════════════════

class TestGetDbConnectionCompatibility:

    def test_function_exists(self):
        assert hasattr(_db_module, 'get_db_connection')

    def test_supports_context_manager_and_percent_s_placeholder(self):
        with _db_module.get_db_connection() as conn:
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
            cur.execute("INSERT INTO demo (name) VALUES (%s) RETURNING id", ("alice",))
            row = cur.fetchone()
            assert row[0] == 1
            conn.commit()

        rows = _db_module.execute_query(
            "SELECT id, name FROM demo WHERE name = %s",
            params=("alice",),
            fetch_all=True
        )
        assert rows == [{"id": 1, "name": "alice"}]
