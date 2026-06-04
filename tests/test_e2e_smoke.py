import importlib
import os
import sys
import types
from datetime import date


def _install_streamlit_stub():
    st = types.ModuleType("streamlit")
    st.cache_data = lambda **kw: (lambda f: f)
    st.session_state = {}
    sys.modules["streamlit"] = st
    return st


def _fresh_app_modules(tmp_path):
    st = _install_streamlit_stub()
    os.environ["SQLITE_DB_PATH"] = str(tmp_path / "smoke.db")
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    sys.modules.pop("bcrypt", None)
    for name in list(sys.modules):
        if name in {"utils.database", "utils.auth", "config.settings"}:
            del sys.modules[name]

    database = importlib.import_module("utils.database")
    assert database.initialize_database() is True
    auth = importlib.import_module("utils.auth")
    return st, database, auth


def _lookup_id(database, table, id_col, name_col, name):
    row = database.execute_query(
        f"SELECT {id_col} AS id FROM {table} WHERE {name_col} = %s",
        params=(name,),
        fetch_one=True,
    )
    assert row, f"missing lookup row {table}.{name_col}={name}"
    return row["id"]


def test_core_business_flow_smoke(tmp_path):
    st, database, auth = _fresh_app_modules(tmp_path)

    assert auth.login_user("admin", "Admin@123")["username"] == "admin"
    assert st.session_state["logged_in"] is True

    idle_status = _lookup_id(database, "mold_statuses", "status_id", "status_name", "闲置")
    loan_pending = _lookup_id(database, "loan_statuses", "status_id", "status_name", "待审批")
    loan_approved = _lookup_id(database, "loan_statuses", "status_id", "status_name", "已批准")
    repair_type = _lookup_id(database, "maintenance_types", "type_id", "type_name", "故障维修")
    repair_done = _lookup_id(database, "maintenance_result_statuses", "status_id", "status_name", "合格可用")
    functional_type = _lookup_id(database, "mold_functional_types", "type_id", "type_name", "冲裁模")
    location = _lookup_id(database, "storage_locations", "location_id", "location_name", "A库1号架")

    database.execute_query(
        """
        INSERT INTO molds (
            mold_code, mold_name, mold_functional_type_id, current_status_id,
            current_location_id, responsible_person_id, accumulated_strokes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        params=("SMOKE-M-001", "冒烟测试模具", functional_type, idle_status, location, st.session_state["user_id"], 0),
        commit=True,
    )
    mold = database.execute_query(
        "SELECT mold_id FROM molds WHERE mold_code = %s",
        params=("SMOKE-M-001",),
        fetch_one=True,
    )
    assert mold

    database.execute_query(
        """
        INSERT INTO mold_loan_records (
            mold_id, applicant_id, loan_status_id, expected_return_date, purpose
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        params=(mold["mold_id"], st.session_state["user_id"], loan_pending, "2026-06-30", "端到端冒烟测试"),
        commit=True,
    )
    loan = database.execute_query(
        "SELECT loan_id, loan_status_id FROM mold_loan_records WHERE mold_id = %s",
        params=(mold["mold_id"],),
        fetch_one=True,
    )
    assert loan["loan_status_id"] == loan_pending

    database.execute_query(
        "UPDATE mold_loan_records SET loan_status_id = %s, updated_at = datetime('now') WHERE loan_id = %s",
        params=(loan_approved, loan["loan_id"]),
        commit=True,
    )
    approved = database.execute_query(
        "SELECT loan_status_id FROM mold_loan_records WHERE loan_id = %s",
        params=(loan["loan_id"],),
        fetch_one=True,
    )
    assert approved["loan_status_id"] == loan_approved

    database.execute_query(
        """
        INSERT INTO mold_maintenance_logs (
            mold_id, maintenance_type_id, technician_id, result_status_id,
            maintenance_start_timestamp, maintenance_end_timestamp, description, cost
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        params=(
            mold["mold_id"],
            repair_type,
            st.session_state["user_id"],
            repair_done,
            "2026-06-04 09:00:00",
            "2026-06-04 11:00:00",
            "冒烟测试维修流转",
            128.5,
        ),
        commit=True,
    )
    maintenance = database.execute_query(
        "SELECT result_status_id, cost FROM mold_maintenance_logs WHERE mold_id = %s",
        params=(mold["mold_id"],),
        fetch_one=True,
    )
    assert maintenance["result_status_id"] == repair_done
    assert maintenance["cost"] == 128.5

    database.execute_query(
        "INSERT INTO products (product_code, product_name) VALUES (%s, %s)",
        params=("SMOKE-P-001", "冒烟测试产品"),
        commit=True,
    )
    product = database.execute_query(
        "SELECT product_id FROM products WHERE product_code = %s",
        params=("SMOKE-P-001",),
        fetch_one=True,
    )
    database.execute_query(
        """
        INSERT INTO production_orders (order_code, product_id, quantity, due_date)
        VALUES (%s, %s, %s, %s)
        """,
        params=("SMOKE-O-001", product["product_id"], 100, str(date(2026, 7, 1))),
        commit=True,
    )
    order = database.execute_query(
        "SELECT order_id FROM production_orders WHERE order_code = %s",
        params=("SMOKE-O-001",),
        fetch_one=True,
    )
    database.execute_query(
        "INSERT INTO production_equipment (equipment_code, equipment_name) VALUES (%s, %s)",
        params=("SMOKE-E-001", "冒烟测试冲床"),
        commit=True,
    )
    equipment = database.execute_query(
        "SELECT equipment_id FROM production_equipment WHERE equipment_code = %s",
        params=("SMOKE-E-001",),
        fetch_one=True,
    )
    database.execute_query(
        """
        INSERT INTO production_schedules (
            order_id, mold_id, equipment_id, scheduled_date, start_time, end_time,
            scheduled_start, scheduled_end, operator_id, quantity, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        params=(
            order["order_id"],
            mold["mold_id"],
            equipment["equipment_id"],
            "2026-06-10",
            "08:00",
            "12:00",
            "2026-06-10 08:00:00",
            "2026-06-10 12:00:00",
            st.session_state["user_id"],
            100,
            "待执行",
        ),
        commit=True,
    )
    schedule = database.execute_query(
        "SELECT status, quantity FROM production_schedules WHERE order_id = %s",
        params=(order["order_id"],),
        fetch_one=True,
    )
    assert schedule == {"status": "待执行", "quantity": 100}
