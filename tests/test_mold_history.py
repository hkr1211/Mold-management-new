# tests/test_mold_history.py — 模具一页式履历回归（真实 schema）
#
# P1 第 2 项：履历页聚合 基本信息/寿命保养/模次曲线/借用史/维修史/部件清单。
# 验证曲线反推计算正确，且四个历史查询能在真实 schema 上执行并取回种子数据。

import os
import sqlite3

from tests.test_mold_management_entrypoint import _build_st_mock, _load_page

_HERE = os.path.dirname(__file__)
_INIT_SQL = os.path.join(_HERE, "..", "sql", "sqlite_init.sql")


def _module():
    st = _build_st_mock({"logged_in": True, "user_role": "超级管理员", "user_id": 1})
    return _load_page(st)


def _real_schema_db():
    conn = sqlite3.connect(":memory:")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row
    return conn


def test_stroke_curve_points():
    m = _module()
    logs = [
        {"时间": "2026-06-01", "模次": 1000},
        {"时间": "2026-06-02", "模次": 500},
        {"时间": "2026-06-03", "模次": -200},  # 手动纠错
    ]
    base, points = m._stroke_curve_points(51300, logs)
    # 建账初始值 = 当前累计 − 流水总和 = 51300 − 1300 = 50000
    assert base == 50000
    assert points == [("2026-06-01", 51000), ("2026-06-02", 51500), ("2026-06-03", 51300)]

    # 无流水：起点即当前值，无点
    base, points = m._stroke_curve_points(8000, [])
    assert base == 8000 and points == []


def test_history_queries_run_on_real_schema_with_seed():
    m = _module()
    conn = _real_schema_db()

    conn.execute("INSERT INTO molds (mold_id, mold_code, mold_name, accumulated_strokes) "
                 "VALUES (1, 'M1', '模具一', 5000)")
    conn.execute("INSERT INTO users (user_id, username, password_hash, full_name, is_active) "
                 "VALUES (9, 'op', 'x', '操作员', 1)")
    conn.execute("INSERT INTO mold_loan_records (mold_id, applicant_id, application_date, purpose) "
                 "VALUES (1, 9, '2026-06-01 09:00:00', '生产借用')")
    conn.execute("INSERT INTO mold_maintenance_logs (mold_id, technician_id, cost, "
                 "strokes_at_maintenance, maintenance_start_timestamp, maintenance_end_timestamp) "
                 "VALUES (1, 9, 350, 4000, '2026-06-02 08:00:00', '2026-06-02 11:00:00')")
    cat_id = conn.execute("SELECT category_id FROM mold_part_categories LIMIT 1").fetchone()
    if cat_id is None:
        conn.execute("INSERT INTO mold_part_categories (category_name) VALUES ('测试类')")
        cat = conn.execute("SELECT category_id FROM mold_part_categories LIMIT 1").fetchone()[0]
    else:
        cat = cat_id[0]
    conn.execute("INSERT INTO mold_parts (mold_id, part_name, part_category_id) "
                 "VALUES (1, '凸模镶块', ?)", (cat,))
    conn.execute("INSERT INTO mold_stroke_logs (mold_id, strokes_added, source_type, operator_id) "
                 "VALUES (1, 1000, 'loan_return', 9)")
    conn.commit()

    def run(query):
        return conn.execute(query.replace("%s", "?"), (1,)).fetchall()

    loans = run(m._build_mold_loan_history_query())
    assert len(loans) == 1 and loans[0]["申请人"] == "操作员"

    maints = run(m._build_mold_maintenance_history_query())
    assert len(maints) == 1
    assert maints[0]["费用"] == 350 and maints[0]["当时模次"] == 4000

    parts = run(m._build_mold_parts_query())
    assert len(parts) == 1 and parts[0]["部件名称"] == "凸模镶块"

    strokes = run(m._build_stroke_logs_query())
    assert len(strokes) == 1
    assert strokes[0]["模次"] == 1000 and strokes[0]["来源"] == "loan_return"
    assert strokes[0]["操作人"] == "操作员"
