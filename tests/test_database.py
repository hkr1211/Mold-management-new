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
# 将 DB_PATH 指向临时内存库，避免在测试环境下创建文件 / 污染真实库
_src_patched = _re.sub(
    r"from config\.settings import \([^)]*\)",
    "DB_PATH = ':memory:'; CACHE_TTL_SECONDS = 300; "
    "LOOKUP_CACHE_TTL = 600; DEFAULT_PAGE_SIZE = 100",
    _src_patched,
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


# ══════════════════════════════════════════════════════════════════
# 错误处理约定：数据库故障降级，编码缺陷上抛（不伪装成空数据）
# ══════════════════════════════════════════════════════════════════

class TestErrorHandlingContract:
    """数据检索函数只吞 sqlite3.Error，其余异常（编码缺陷）必须上抛。"""

    def test_db_error_returns_safe_default(self):
        # 查询不存在的表 → sqlite3.OperationalError → 降级返回 []，UI 不崩
        assert _db_module.get_all_molds() == []

    def test_programming_error_propagates(self):
        # 传入非白名单表名属编码缺陷：应抛 ValueError，而非被吞成 []
        with pytest.raises(ValueError):
            _db_module.get_table_info('definitely_not_a_whitelisted_table')

    def test_execute_query_reraises_on_bad_sql(self):
        # 核心查询函数遇到 SQL 错误必须抛出，由调用方决定如何处理
        import sqlite3
        with pytest.raises(sqlite3.Error):
            _db_module.execute_query("SELECT * FROM no_such_table_xyz", fetch_all=True)

    def test_validators_surface_bad_identifier(self):
        # 校验函数收到非白名单表名属编码缺陷：应抛 ValueError，而非被吞成 False
        with pytest.raises(ValueError):
            _db_module.validate_foreign_key('not_whitelisted_table', 'col', 1)
        with pytest.raises(ValueError):
            _db_module.validate_unique_constraint('not_whitelisted_table', 'col', 1)


# ══════════════════════════════════════════════════════════════════
# add_mold_strokes — 模次累计唯一入口（台账 + 流水同事务）
# ══════════════════════════════════════════════════════════════════

class TestAddMoldStrokes:

    @classmethod
    def setup_class(cls):
        # 在本模块的 :memory: 库上加载真实 schema，并准备一个测试模具
        init_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'sqlite_init.sql')
        conn = _db_module._get_conn()
        with open(init_path, encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.execute(
            "INSERT OR IGNORE INTO molds (mold_id, mold_code, mold_name, accumulated_strokes) "
            "VALUES (901, 'TST-901', '模次测试模具', 1000)"
        )
        conn.commit()

    def test_accumulates_ledger_and_writes_log(self):
        ok, msg = _db_module.add_mold_strokes(
            901, 500, 'loan_return', source_id=12, operator_id=1, remarks='借用单 12 归还')
        assert ok, msg

        row = _db_module.execute_query(
            "SELECT accumulated_strokes FROM molds WHERE mold_id = 901", fetch_one=True)
        assert row['accumulated_strokes'] == 1500

        log = _db_module.execute_query(
            "SELECT * FROM mold_stroke_logs WHERE mold_id = 901 "
            "ORDER BY stroke_log_id DESC LIMIT 1", fetch_one=True)
        assert log['strokes_added'] == 500
        assert log['source_type'] == 'loan_return'
        assert log['source_id'] == '12'
        assert log['operator_id'] == 1

    def test_zero_strokes_rejected(self):
        ok, msg = _db_module.add_mold_strokes(901, 0, 'loan_return')
        assert not ok

    def test_nonexistent_mold_rejected_without_orphan_log(self):
        before = _db_module.execute_query(
            "SELECT COUNT(*) AS n FROM mold_stroke_logs", fetch_one=True)['n']
        ok, msg = _db_module.add_mold_strokes(999999, 100, 'loan_return')
        assert not ok
        after = _db_module.execute_query(
            "SELECT COUNT(*) AS n FROM mold_stroke_logs", fetch_one=True)['n']
        assert after == before  # 事务回滚，不留孤儿流水

    def test_negative_manual_adjust_allowed(self):
        row = _db_module.execute_query(
            "SELECT accumulated_strokes FROM molds WHERE mold_id = 901", fetch_one=True)
        base = row['accumulated_strokes']
        ok, _ = _db_module.add_mold_strokes(901, -200, 'manual_adjust', remarks='纠错回调')
        assert ok
        row = _db_module.execute_query(
            "SELECT accumulated_strokes FROM molds WHERE mold_id = 901", fetch_one=True)
        assert row['accumulated_strokes'] == base - 200
