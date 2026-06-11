# pages/1_模具管理.py
import streamlit as st
import pandas as pd
import logging
import sqlite3
from datetime import date
from utils.database import (
    execute_query, get_all_molds, get_mold_statuses,
    get_storage_locations, get_functional_types
)
from utils.auth import has_permission, log_user_action
from utils.ui import inject_global_css, page_header
from utils.nav import setup_sidebar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_or_stop(fn, *args, **kwargs):
    """执行数据读取：DB 故障时提示“加载失败”并停止本次渲染（区别于“暂无数据”）；
    编码缺陷（非 sqlite3.Error）照常上抛暴露。"""
    try:
        return fn(*args, **kwargs)
    except sqlite3.Error as e:
        logger.error(f"数据加载失败: {e}")
        st.error(f"❌ 数据加载失败：{e}")
        st.stop()

inject_global_css()

# --- 访问控制 ---
if not st.session_state.get('logged_in', False):
    st.error("🔒 请先登录以访问此页面。")
    st.stop()

if not has_permission('view_molds'):
    st.error("❌ 权限不足：您无法访问模具管理功能。")
    st.stop()

setup_sidebar("1_模具管理.py")
page_header("🛠️", "模具管理", "模具台账 · 新增 · 编辑")

# --- 数据加载 ---
@st.cache_data(ttl=300)
def load_molds(search_code="", search_name="", status_filter="全部", page=1, page_size=100):
    # 不再吞异常：DB 故障与编码缺陷一律上抛，由调用方（_load_or_stop）区分
    # 展示“加载失败”与“暂无数据”。
    where_clauses = []
    params = []

    if search_code:
        where_clauses.append("m.mold_code LIKE %s")
        params.append(f"%{search_code}%")
    if search_name:
        where_clauses.append("m.mold_name LIKE %s")
        params.append(f"%{search_name}%")
    if status_filter != "全部":
        where_clauses.append("ms.status_name = %s")
        params.append(status_filter)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    offset = max(page - 1, 0) * page_size
    query = """
    SELECT
        m.mold_id,
        m.mold_code        AS 模具编号,
        m.mold_name        AS 模具名称,
        mft.type_name      AS 功能类型,
        ms.status_name     AS 当前状态,
        sl.location_name   AS 存放位置,
        m.accumulated_strokes         AS 累计模次,
        m.theoretical_lifespan_strokes AS 理论寿命,
        m.maintenance_cycle_strokes    AS 保养周期,
        u.full_name        AS 负责人,
        m.supplier         AS 供应商,
        m.remarks          AS 备注,
        m.created_at       AS 创建时间
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
    LEFT JOIN users u ON m.responsible_person_id = u.user_id
    {where_sql}
    ORDER BY m.created_at DESC
    LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = execute_query(query.format(where_sql=where_sql), params=tuple(params), fetch_all=True) or []
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def load_lookup_data():
    statuses = get_mold_statuses() or []
    locations = get_storage_locations() or []
    types = get_functional_types() or []
    users_raw = execute_query(
        "SELECT user_id, full_name FROM users WHERE is_active = true ORDER BY full_name",
        fetch_all=True
    ) or []
    return statuses, locations, types, users_raw

# --- 主页面 ---

tab1, tab2, tab3 = st.tabs(["📋 模具列表", "➕ 新增模具", "✏️ 编辑模具"])

# ========== TAB1：模具列表 ==========
with tab1:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        search_code = st.text_input("按编号搜索", placeholder="输入模具编号...", key="search_code")
    with col2:
        search_name = st.text_input("按名称搜索", placeholder="输入模具名称...", key="search_name")
    with col3:
        statuses, _, _, _ = _load_or_stop(load_lookup_data)
        status_names = ["全部"] + [s['status_name'] for s in statuses]
        status_filter = st.selectbox("状态筛选", status_names, key="status_filter")

    page_col, size_col, _ = st.columns([1, 1, 4])
    page = page_col.number_input("页码", min_value=1, value=1, step=1, key="mold_page")
    page_size = size_col.selectbox("每页", [50, 100, 200], index=1, key="mold_page_size")

    col_refresh, col_export = st.columns([1, 7])
    with col_refresh:
        if st.button("🔄 刷新", key="refresh_list"):
            st.cache_data.clear()
            st.rerun()

    df = _load_or_stop(load_molds, search_code, search_name, status_filter, page, page_size)

    if df.empty:
        st.info("暂无符合条件的模具记录。")
    else:
        display_cols = ['模具编号', '模具名称', '功能类型', '当前状态', '存放位置',
                        '累计模次', '理论寿命', '保养周期', '负责人']
        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"当前第 {page} 页，显示 {len(df)} 条记录")

        # 选中某行显示详情
        if not df.empty:
            with st.expander("🔍 查看详情", expanded=False):
                selected_code = st.selectbox(
                    "选择模具编号",
                    df['模具编号'].tolist(),
                    key="detail_select"
                )
                row = df[df['模具编号'] == selected_code].iloc[0]
                c1, c2 = st.columns(2)
                for i, (col, val) in enumerate(row.items()):
                    if col == 'mold_id':
                        continue
                    (c1 if i % 2 == 0 else c2).markdown(f"**{col}**：{val}")

# ========== TAB2：新增模具 ==========
with tab2:
    if not has_permission('manage_molds'):
        st.warning("🔒 您的角色没有新增模具的权限。")
    else:
        statuses, locations, types, users_raw = _load_or_stop(load_lookup_data)

        with st.form("add_mold_form", clear_on_submit=True):
            st.subheader("基本信息")
            c1, c2 = st.columns(2)
            mold_code = c1.text_input("模具编号 *", placeholder="例：MD-2024-001")
            mold_name = c2.text_input("模具名称 *", placeholder="例：前门外板拉延模")
            drawing_number = c1.text_input("图号", placeholder="DWG-001")
            supplier = c2.text_input("供应商")

            type_options = {t['type_name']: t['type_id'] for t in types}
            functional_type = c1.selectbox(
                "功能类型",
                ["（未选择）"] + list(type_options.keys())
            )
            mfg_date = c2.date_input("制造日期", value=date.today())

            st.subheader("技术参数")
            c3, c4, c5 = st.columns(3)
            lifespan = c3.number_input("理论寿命（模次）", min_value=0, value=500000, step=10000)
            cycle = c4.number_input("保养周期（模次）", min_value=0, value=50000, step=5000)
            accumulated = c5.number_input("当前累计模次", min_value=0, value=0, step=1000)

            st.subheader("存放信息")
            c6, c7 = st.columns(2)
            status_options = {s['status_name']: s['status_id'] for s in statuses}
            init_status = c6.selectbox(
                "初始状态",
                list(status_options.keys()),
                index=list(status_options.keys()).index('闲置') if '闲置' in status_options else 0
            )
            location_options = {l['location_name']: l['location_id'] for l in locations}
            location = c7.selectbox("存放位置", ["（未选择）"] + list(location_options.keys()))

            user_options = {u['full_name']: u['user_id'] for u in users_raw}
            responsible = st.selectbox("负责人", ["（未选择）"] + list(user_options.keys()))
            remarks = st.text_area("备注", height=80)

            submitted = st.form_submit_button("➕ 创建模具", type="primary")

        if submitted:
            if not mold_code.strip():
                st.error("❌ 模具编号不能为空")
            elif not mold_name.strip():
                st.error("❌ 模具名称不能为空")
            else:
                # 检查编号唯一性
                exists = _load_or_stop(
                    execute_query,
                    "SELECT mold_id FROM molds WHERE mold_code = %s",
                    params=(mold_code.strip(),), fetch_one=True
                )
                if exists:
                    st.error(f"❌ 模具编号 {mold_code} 已存在")
                else:
                    type_id = type_options.get(functional_type) if functional_type != "（未选择）" else None
                    loc_id = location_options.get(location) if location != "（未选择）" else None
                    resp_id = user_options.get(responsible) if responsible != "（未选择）" else None
                    status_id = status_options[init_status]

                    insert_sql = """
                    INSERT INTO molds (
                        mold_code, mold_name, mold_drawing_number, supplier,
                        mold_functional_type_id, manufacturing_date,
                        theoretical_lifespan_strokes, maintenance_cycle_strokes, accumulated_strokes,
                        current_status_id, current_location_id, responsible_person_id,
                        remarks, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    """
                    try:
                        execute_query(insert_sql, params=(
                            mold_code.strip(), mold_name.strip(), drawing_number.strip() or None,
                            supplier.strip() or None, type_id, mfg_date,
                            lifespan, cycle, accumulated,
                            status_id, loc_id, resp_id,
                            remarks.strip() or None
                        ), commit=True)
                        log_user_action('CREATE_MOLD', 'molds', mold_code.strip())
                        st.success(f"✅ 模具 {mold_code} 创建成功！")
                        st.cache_data.clear()
                    except sqlite3.Error as e:
                        logger.error(f"创建模具失败: {e}")
                        st.error(f"❌ 创建失败：{e}")

# ========== TAB3：编辑模具 ==========
with tab3:
    if not has_permission('manage_molds'):
        st.warning("🔒 您的角色没有编辑模具的权限。")
    else:
        edit_code = st.text_input("输入要编辑的模具编号", key="edit_code_input")
        if st.button("🔍 查询", key="edit_search"):
            st.session_state['edit_mold_code'] = edit_code.strip()

        code_to_edit = st.session_state.get('edit_mold_code', '')
        if code_to_edit:
            mold_row = _load_or_stop(
                execute_query,
                """
                SELECT m.*, ms.status_name, sl.location_name, mft.type_name,
                       u.full_name as responsible_name
                FROM molds m
                LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
                LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
                LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
                LEFT JOIN users u ON m.responsible_person_id = u.user_id
                WHERE m.mold_code = %s
                """,
                params=(code_to_edit,), fetch_one=True
            )

            if not mold_row:
                st.error(f"❌ 未找到模具编号：{code_to_edit}")
            else:
                statuses, locations, types, users_raw = _load_or_stop(load_lookup_data)
                status_options = {s['status_name']: s['status_id'] for s in statuses}
                location_options = {l['location_name']: l['location_id'] for l in locations}
                type_options = {t['type_name']: t['type_id'] for t in types}
                user_options = {u['full_name']: u['user_id'] for u in users_raw}

                with st.form("edit_mold_form"):
                    st.subheader(f"编辑：{mold_row['mold_code']} — {mold_row['mold_name']}")
                    c1, c2 = st.columns(2)
                    new_name = c1.text_input("模具名称 *", value=mold_row.get('mold_name', ''))
                    new_supplier = c2.text_input("供应商", value=mold_row.get('supplier', '') or '')

                    c3, c4 = st.columns(2)
                    cur_status = mold_row.get('status_name', '')
                    status_keys = list(status_options.keys())
                    s_idx = status_keys.index(cur_status) if cur_status in status_keys else 0
                    new_status = c3.selectbox("状态", status_keys, index=s_idx)

                    cur_loc = mold_row.get('location_name', '')
                    loc_keys = ["（未选择）"] + list(location_options.keys())
                    l_idx = loc_keys.index(cur_loc) if cur_loc in loc_keys else 0
                    new_location = c4.selectbox("存放位置", loc_keys, index=l_idx)

                    c5, c6, c7 = st.columns(3)
                    new_lifespan = c5.number_input(
                        "理论寿命", min_value=0,
                        value=int(mold_row.get('theoretical_lifespan_strokes') or 0)
                    )
                    new_cycle = c6.number_input(
                        "保养周期", min_value=0,
                        value=int(mold_row.get('maintenance_cycle_strokes') or 0)
                    )
                    new_accumulated = c7.number_input(
                        "累计模次", min_value=0,
                        value=int(mold_row.get('accumulated_strokes') or 0)
                    )

                    cur_resp = mold_row.get('responsible_name', '')
                    resp_keys = ["（未选择）"] + list(user_options.keys())
                    r_idx = resp_keys.index(cur_resp) if cur_resp in resp_keys else 0
                    new_responsible = st.selectbox("负责人", resp_keys, index=r_idx)
                    new_remarks = st.text_area("备注", value=mold_row.get('remarks', '') or '')

                    save = st.form_submit_button("💾 保存修改", type="primary")

                if save:
                    if not new_name.strip():
                        st.error("❌ 模具名称不能为空")
                    else:
                        loc_id = location_options.get(new_location) if new_location != "（未选择）" else None
                        resp_id = user_options.get(new_responsible) if new_responsible != "（未选择）" else None
                        update_sql = """
                        UPDATE molds SET
                            mold_name = %s, supplier = %s,
                            current_status_id = %s, current_location_id = %s,
                            theoretical_lifespan_strokes = %s,
                            maintenance_cycle_strokes = %s, accumulated_strokes = %s,
                            responsible_person_id = %s, remarks = %s,
                            updated_at = NOW()
                        WHERE mold_code = %s
                        """
                        try:
                            execute_query(update_sql, params=(
                                new_name.strip(), new_supplier.strip() or None,
                                status_options[new_status], loc_id,
                                new_lifespan, new_cycle, new_accumulated,
                                resp_id, new_remarks.strip() or None,
                                code_to_edit
                            ), commit=True)
                            # 手动改动累计模次 → 记入模次流水（manual_adjust），保证台账可审计
                            old_accumulated = int(mold_row.get('accumulated_strokes') or 0)
                            delta = int(new_accumulated) - old_accumulated
                            if delta != 0:
                                execute_query(
                                    "INSERT INTO mold_stroke_logs "
                                    "(mold_id, strokes_added, source_type, source_id, operator_id, remarks) "
                                    "VALUES (%s, %s, 'manual_adjust', %s, %s, %s)",
                                    params=(mold_row['mold_id'], delta, code_to_edit,
                                            st.session_state.get('user_id'),
                                            f"台账编辑：{old_accumulated} → {new_accumulated}"),
                                    commit=True
                                )
                            log_user_action('UPDATE_MOLD', 'molds', code_to_edit)
                            st.success(f"✅ 模具 {code_to_edit} 更新成功！")
                            st.cache_data.clear()
                            del st.session_state['edit_mold_code']
                        except sqlite3.Error as e:
                            logger.error(f"更新模具失败: {e}")
                            st.error(f"❌ 更新失败：{e}")
