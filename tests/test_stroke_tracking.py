# tests/test_stroke_tracking.py — 模次累计与保养预警语义回归测试（真实 schema）
#
# 背景：此前 (1) accumulated_strokes 无业务累计入口；(2) 保养预警条件为
# "累计模次 >= 周期"，模具过第一个周期后永久报警，保养完成也不消警。
# 本测试在 sqlite_init.sql 构建的内存库上锁定修复后的语义：
#   - 预警按"累计模次 − 最近一次已完成保养的 strokes_at_maintenance ≥ 周期"判定；
#   - 保养完成后消警；再次累计满一个周期后重新报警；
#   - 寿命 90% 预警维持原语义。

import os
import re
import sqlite3
import sys
import types

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")
_PAGE = os.path.join(_HERE, "..", "app", "pages", "3_维修管理.py")


def _real_schema_db():
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row
    return conn


def _load_alert_query():
    """加载维修页模块（剥离末尾 show()），取出预警 SQL 构建函数。"""
    st = types.ModuleType("streamlit")
    st.session_state = {}
    for name in ("error", "warning", "info", "success", "markdown", "subheader",
                 "write", "metric", "caption"):
        setattr(st, name, lambda *a, **kw: None)
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

    with open(_PAGE, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"^show\(\)\s*$", "", src, flags=re.MULTILINE)

    module = types.ModuleType("maintenance_page")
    exec(compile(src, "3_维修管理.py", "exec"), module.__dict__)
    return module._build_molds_needing_maintenance_query()


def _insert_mold(conn, mold_id, code, accumulated, cycle=None, lifespan=None):
    conn.execute(
        "INSERT INTO molds (mold_id, mold_code, mold_name, accumulated_strokes, "
        "maintenance_cycle_strokes, theoretical_lifespan_strokes) VALUES (?,?,?,?,?,?)",
        (mold_id, code, f"测试模具{code}", accumulated, cycle, lifespan),
    )


def _insert_completed_maintenance(conn, mold_id, strokes_at):
    conn.execute(
        "INSERT INTO mold_maintenance_logs (mold_id, maintenance_end_timestamp, "
        "strokes_at_maintenance) VALUES (?, datetime('now'), ?)",
        (mold_id, strokes_at),
    )


def test_alert_semantics_on_real_schema():
    conn = _real_schema_db()
    query = _load_alert_query()

    # A：周期5万，累计12万，最近保养发生在10万模次 → 距上次2万 < 周期 → 不报警（保养消警）
    _insert_mold(conn, 1, "A", accumulated=120000, cycle=50000)
    _insert_completed_maintenance(conn, 1, strokes_at=100000)

    # B：同样累计12万但从未保养 → 距上次=12万 ≥ 周期 → 报警
    _insert_mold(conn, 2, "B", accumulated=120000, cycle=50000)

    # C：保养发生在10万，此后又累计到16万 → 距上次6万 ≥ 周期 → 重新报警
    _insert_mold(conn, 3, "C", accumulated=160000, cycle=50000)
    _insert_completed_maintenance(conn, 3, strokes_at=100000)

    # D：无保养周期，但累计达寿命的95% → 即将到期
    _insert_mold(conn, 4, "D", accumulated=95000, lifespan=100000)
    conn.commit()

    rows = {r["mold_code"]: dict(r) for r in conn.execute(query).fetchall()}

    assert "A" not in rows, "保养完成后应消警（旧逻辑会永久报警）"
    assert rows["B"]["maintenance_status"] == "需要保养"
    assert rows["B"]["strokes_since_maintenance"] == 120000
    assert rows["C"]["maintenance_status"] == "需要保养", "保养后再满一个周期应重新报警"
    assert rows["C"]["strokes_since_maintenance"] == 60000
    assert rows["D"]["maintenance_status"] == "即将到期"


def test_unmaintained_mold_under_cycle_not_alerted():
    conn = _real_schema_db()
    query = _load_alert_query()
    # 新模具累计 3 万 < 周期 5 万 → 不报警
    _insert_mold(conn, 1, "NEW", accumulated=30000, cycle=50000)
    conn.commit()
    rows = conn.execute(query).fetchall()
    assert rows == []
