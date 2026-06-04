import os
import re


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def test_system_management_has_no_blocking_sleep_or_cpu_interval():
    src = _read("app/pages/5_系统管理.py")

    assert "time.sleep" not in src
    assert "psutil.cpu_percent(interval=1)" not in src
    assert "psutil.cpu_percent(interval=0)" in src


def test_mold_list_filters_and_paginates_in_sql():
    src = _read("app/pages/1_模具管理.py")
    match = re.search(r"def load_molds\([^)]*\):(?P<body>.*?)@st\.cache_data", src, re.S)
    assert match, "load_molds body not found"
    body = match.group("body")

    assert "LIMIT %s OFFSET %s" in body
    assert "m.mold_code LIKE %s" in body
    assert "m.mold_name LIKE %s" in body
    assert "ms.status_name = %s" in body
    assert "str.contains" not in body


def test_part_list_filters_and_paginates_in_sql():
    src = _read("app/pages/4_部件管理.py")
    match = re.search(r"def load_parts\([^)]*\):(?P<body>.*?)@st\.cache_data", src, re.S)
    assert match, "load_parts body not found"
    body = match.group("body")

    assert "LIMIT %s OFFSET %s" in body
    assert "m.mold_code LIKE %s" in body
    assert "c.category_name = %s" in body
    assert "ms.status_name = %s" in body
    assert "str.contains" not in body
