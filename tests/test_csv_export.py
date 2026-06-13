# tests/test_csv_export.py — CSV 导出 helper 回归（utils.ui.build_csv_bytes）

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


def _load_ui():
    # ui.py 仅依赖 streamlit；build_csv_bytes 只用 pandas，mock 掉 st 即可
    st = types.ModuleType("streamlit")
    st.markdown = lambda *a, **kw: None
    sys.modules["streamlit"] = st
    import importlib
    import utils.ui as ui
    importlib.reload(ui)
    return ui


def test_csv_has_utf8_bom_for_excel():
    ui = _load_ui()
    out = ui.build_csv_bytes([{"模具编号": "MD-1", "制作人": "张三"}])
    assert out.startswith(b"\xef\xbb\xbf"), "缺 UTF-8 BOM，Excel 打开会中文乱码"
    text = out.decode("utf-8-sig")
    assert "模具编号" in text and "MD-1" in text and "张三" in text


def test_columns_subset_and_order():
    ui = _load_ui()
    rows = [{"a": 1, "b": 2, "c": 3}]
    out = ui.build_csv_bytes(rows, columns=["c", "a"]).decode("utf-8-sig")
    header = out.splitlines()[0].strip()
    assert header == "c,a"  # 仅导出指定列，按指定顺序


def test_empty_data_returns_header_only_or_empty():
    ui = _load_ui()
    # 空 list → 无表头的空内容，不抛异常
    assert ui.build_csv_bytes([]).decode("utf-8-sig").strip() == ""


def test_accepts_dataframe():
    ui = _load_ui()
    import pandas as pd
    df = pd.DataFrame([{"x": "一", "y": "二"}])
    out = ui.build_csv_bytes(df).decode("utf-8-sig")
    assert "x,y" in out and "一,二" in out


def test_unknown_columns_ignored():
    ui = _load_ui()
    out = ui.build_csv_bytes([{"a": 1}], columns=["a", "missing"]).decode("utf-8-sig")
    assert out.splitlines()[0].strip() == "a"  # 不存在的列被忽略，不报错
