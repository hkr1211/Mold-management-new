# tests/test_mold_io.py — 模具 Excel 批量导入/导出回归（真实 schema）

import io
import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from utils import mold_io  # noqa: E402

_INIT_SQL = os.path.join(os.path.dirname(__file__), "..", "sql", "sqlite_init.sql")


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    with open(_INIT_SQL, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.row_factory = sqlite3.Row
    return conn


def _eq(conn):
    def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        cur = conn.execute(query.replace("%s", "?").replace("NOW()", "datetime('now')"),
                           params or ())
        if fetch_one:
            r = cur.fetchone()
            return dict(r) if r else None
        if fetch_all:
            return [dict(r) for r in cur.fetchall()]
        if commit:
            conn.commit()
        return cur.rowcount
    return execute_query


def _lookups(conn):
    def m(table, idc, namec):
        return {r[namec]: r[idc] for r in conn.execute(f"SELECT {idc},{namec} FROM {table}")}
    conn.execute("INSERT INTO users (user_id, username, password_hash, full_name, is_active) "
                 "VALUES (5,'u','x','王工',1)")
    conn.commit()
    return {
        "type": m("mold_functional_types", "type_id", "type_name"),
        "status": m("mold_statuses", "status_id", "status_name"),
        "location": m("storage_locations", "location_id", "location_name"),
        "user": {"王工": 5},
    }


def test_template_has_headers_only():
    df = pd.read_excel(io.BytesIO(mold_io.build_template_bytes()), engine="openpyxl")
    assert len(df) == 0  # 仅表头无数据
    cols = [c.rstrip("*") for c in df.columns]
    for required in ("模具编号", "模具名称", "制作人", "模具规格", "功能类型", "状态"):
        assert required in cols


def test_export_roundtrip_columns():
    out = mold_io.build_export_bytes([
        {"模具编号": "MD-1", "模具名称": "甲", "制作人": "李四"}])
    df = pd.read_excel(io.BytesIO(out), engine="openpyxl")
    assert list(df.columns) == mold_io.MOLD_COLUMNS  # 标准列、固定顺序
    assert df.iloc[0]["模具编号"] == "MD-1"


def _import(conn, rows):
    df = pd.DataFrame(rows)
    return mold_io.import_molds(df, _lookups(conn), _eq(conn))


def test_import_creates_and_updates():
    conn = _db()
    lk = _lookups(conn)
    status_name = next(iter(lk["status"]))
    loc_name = next(iter(lk["location"]))
    typ_name = next(iter(lk["type"]))

    df = pd.DataFrame([
        {"模具编号": "MD-100", "模具名称": "拉延模", "制作人": "李四",
         "模具规格": "100x100", "功能类型": typ_name, "状态": status_name,
         "存放位置": loc_name, "负责人": "王工", "理论寿命": "500000",
         "保养周期": "50000", "累计模次": "1000"},
    ])
    res = mold_io.import_molds(df, lk, _eq(conn))
    assert res == {"created": 1, "updated": 0, "errors": []}
    row = conn.execute("SELECT * FROM molds WHERE mold_code='MD-100'").fetchone()
    assert row["mold_name"] == "拉延模" and row["maker"] == "李四"
    assert row["specification"] == "100x100" and row["accumulated_strokes"] == 1000

    # 再次导入同编号 → 更新；累计模次不被覆盖
    df2 = pd.DataFrame([{"模具编号": "MD-100", "模具名称": "拉延模(改)",
                         "累计模次": "999999"}])
    res2 = mold_io.import_molds(df2, lk, _eq(conn))
    assert res2["updated"] == 1 and res2["created"] == 0
    row = conn.execute("SELECT * FROM molds WHERE mold_code='MD-100'").fetchone()
    assert row["mold_name"] == "拉延模(改)"
    assert row["accumulated_strokes"] == 1000  # 更新不动累计模次


def test_import_row_errors():
    conn = _db()
    lk = _lookups(conn)
    df = pd.DataFrame([
        {"模具编号": "", "模具名称": "缺编号"},                       # 必填缺失
        {"模具编号": "MD-9", "模具名称": "未知类型", "功能类型": "不存在的类型"},
        {"模具编号": "MD-10", "模具名称": "正常"},                    # OK
    ])
    res = mold_io.import_molds(df, lk, _eq(conn))
    assert res["created"] == 1
    assert len(res["errors"]) == 2
    # 行号为表头后第几行（2 起）
    err_rows = {r[0] for r in res["errors"]}
    assert err_rows == {2, 3}


def test_import_missing_required_column():
    conn = _db()
    df = pd.DataFrame([{"模具编号": "X"}])  # 缺"模具名称"列
    res = mold_io.import_molds(df, _lookups(conn), _eq(conn))
    assert res["created"] == 0 and res["errors"]
