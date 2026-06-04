import importlib.util
import os
import sys
import types


def _install_streamlit_stub():
    st = types.ModuleType("streamlit")
    st.cache_data = lambda **kw: (lambda f: f)
    st.session_state = {}
    sys.modules["streamlit"] = st
    return st


def _load_database_module(tmp_path):
    _install_streamlit_stub()
    db_path = tmp_path / "startup.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    module_path = os.path.join(app_dir, "utils", "database.py")
    sys.modules.pop("config.settings", None)
    spec = importlib.util.spec_from_file_location("database_startup_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, db_path


def test_database_import_does_not_initialize_sqlite_file(tmp_path):
    module, db_path = _load_database_module(tmp_path)

    assert module.DB_PATH == str(db_path)
    assert not db_path.exists()


def test_initialize_database_explicitly_creates_schema(tmp_path):
    module, db_path = _load_database_module(tmp_path)

    assert module.initialize_database() is True

    assert db_path.exists()
    admin = module.execute_query(
        "SELECT username FROM users WHERE username = %s",
        params=("admin",),
        fetch_one=True,
    )
    assert admin == {"username": "admin"}


def test_ensure_database_initialized_runs_once_per_process(tmp_path):
    module, _ = _load_database_module(tmp_path)
    calls = []

    def fake_initialize():
        calls.append("called")
        return True

    module.initialize_database = fake_initialize

    assert module.ensure_database_initialized() is True
    assert module.ensure_database_initialized() is True

    assert calls == ["called"]


def test_sqlite_connection_uses_busy_timeout(tmp_path):
    module, _ = _load_database_module(tmp_path)

    conn = module._get_conn()

    busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert busy_timeout == 30000
