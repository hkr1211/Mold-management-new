# app/utils/mold_io.py — 模具信息 Excel 批量导入/导出
#
# 与 Streamlit 解耦：纯函数 + 注入 execute_query，便于单元测试。
import io
import sqlite3
import pandas as pd

# 模板/导入/导出的标准列（顺序即模板列顺序）；带 * 的为必填
MOLD_COLUMNS = [
    "模具编号", "模具名称", "图号", "制作人", "模具规格",
    "功能类型", "制造日期", "理论寿命", "保养周期", "累计模次",
    "状态", "存放位置", "负责人", "备注",
]
REQUIRED_COLUMNS = ["模具编号", "模具名称"]
# 通过名称解析为外键 id 的列：列名 → lookups 子字典键
_LOOKUP_COLUMNS = {
    "功能类型": "type",
    "状态": "status",
    "存放位置": "location",
    "负责人": "user",
}


def _df_to_xlsx(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="模具信息")
    buf.seek(0)
    return buf.getvalue()


def build_template_bytes() -> bytes:
    """仅含表头的空模板，供管理员按格式填写。"""
    header = list(MOLD_COLUMNS)
    header[header.index("模具编号")] = "模具编号*"
    header[header.index("模具名称")] = "模具名称*"
    return _df_to_xlsx(pd.DataFrame(columns=header))


def build_export_bytes(rows) -> bytes:
    """把模具行（dict 列表，键为 MOLD_COLUMNS）导出为 xlsx；缺列补空、按标准列排序。"""
    df = pd.DataFrame(list(rows) if rows else [], columns=MOLD_COLUMNS)
    for c in MOLD_COLUMNS:
        if c not in df.columns:
            df[c] = None
    return _df_to_xlsx(df[MOLD_COLUMNS])


def export_query() -> str:
    """导出用 SELECT，列别名与 MOLD_COLUMNS 完全一致，可与导入往返。"""
    return """
    SELECT
        m.mold_code AS 模具编号, m.mold_name AS 模具名称, m.mold_drawing_number AS 图号,
        m.maker AS 制作人, m.specification AS 模具规格, mft.type_name AS 功能类型,
        m.manufacturing_date AS 制造日期, m.theoretical_lifespan_strokes AS 理论寿命,
        m.maintenance_cycle_strokes AS 保养周期, m.accumulated_strokes AS 累计模次,
        ms.status_name AS 状态, sl.location_name AS 存放位置,
        u.full_name AS 负责人, m.remarks AS 备注
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN mold_statuses ms          ON m.current_status_id        = ms.status_id
    LEFT JOIN storage_locations sl      ON m.current_location_id      = sl.location_id
    LEFT JOIN users u                   ON m.responsible_person_id    = u.user_id
    ORDER BY m.mold_code
    """


def parse_upload(file) -> pd.DataFrame:
    """读取上传的 xlsx；全部按字符串读取（避免编号被转成数字），表头去空白/去 *。"""
    df = pd.read_excel(file, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip().rstrip("*").strip() for c in df.columns]
    return df


def _cell(row, col):
    """取单元格清洗后的字符串；空/NaN 返回 None。"""
    if col not in row:
        return None
    v = row[col]
    try:
        if v is None or pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None


def _to_int(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s == "" or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def import_molds(df: pd.DataFrame, lookups: dict, execute_query) -> dict:
    """按「模具编号」逐行 upsert。

    lookups: {'type':{名:id}, 'status':{名:id}, 'location':{名:id}, 'user':{名:id}}
    返回 {'created':int, 'updated':int, 'errors':[(行号, 原因)]}。
    约定：累计模次仅在新建时写入；更新已存在模具时不动累计模次（由模次流水驱动，
    避免批量导入静默覆盖已统计的冲次）。
    """
    result = {"created": 0, "updated": 0, "errors": []}

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        result["errors"].append((1, f"缺少必需列：{'、'.join(missing_cols)}"))
        return result

    for i, row in df.iterrows():
        rownum = int(i) + 2  # 表头第 1 行，数据从第 2 行起
        code = _cell(row, "模具编号")
        name = _cell(row, "模具名称")
        if not code or not name:
            result["errors"].append((rownum, "模具编号、模具名称为必填"))
            continue

        # 名称 → 外键 id
        ids, bad = {}, None
        for col, key in _LOOKUP_COLUMNS.items():
            nm = _cell(row, col)
            if nm is None:
                ids[key] = None
                continue
            rid = lookups.get(key, {}).get(nm)
            if rid is None:
                bad = f"{col}「{nm}」不存在，请先在主数据中维护或更正"
                break
            ids[key] = rid
        if bad:
            result["errors"].append((rownum, bad))
            continue

        lifespan = _to_int(_cell(row, "理论寿命"))
        cycle = _to_int(_cell(row, "保养周期"))
        accumulated = _to_int(_cell(row, "累计模次")) or 0
        drawing = _cell(row, "图号")
        maker = _cell(row, "制作人")
        spec = _cell(row, "模具规格")
        mfg = _cell(row, "制造日期")
        remarks = _cell(row, "备注")

        try:
            existing = execute_query(
                "SELECT mold_id FROM molds WHERE mold_code = %s",
                params=(code,), fetch_one=True)
            if existing:
                execute_query(
                    """
                    UPDATE molds SET
                        mold_name = %s, mold_drawing_number = %s, maker = %s,
                        specification = %s, mold_functional_type_id = %s,
                        manufacturing_date = %s, theoretical_lifespan_strokes = %s,
                        maintenance_cycle_strokes = %s,
                        current_status_id = COALESCE(%s, current_status_id),
                        current_location_id = %s, responsible_person_id = %s,
                        remarks = %s, updated_at = NOW()
                    WHERE mold_code = %s
                    """,
                    params=(name, drawing, maker, spec, ids["type"], mfg, lifespan,
                            cycle, ids["status"], ids["location"], ids["user"],
                            remarks, code), commit=True)
                result["updated"] += 1
            else:
                execute_query(
                    """
                    INSERT INTO molds (
                        mold_code, mold_name, mold_drawing_number, maker, specification,
                        mold_functional_type_id, manufacturing_date,
                        theoretical_lifespan_strokes, maintenance_cycle_strokes,
                        accumulated_strokes, current_status_id, current_location_id,
                        responsible_person_id, remarks, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    """,
                    params=(code, name, drawing, maker, spec, ids["type"], mfg,
                            lifespan, cycle, accumulated, ids["status"],
                            ids["location"], ids["user"], remarks), commit=True)
                result["created"] += 1
        except sqlite3.Error as e:
            result["errors"].append((rownum, f"写入失败：{e}"))

    return result
