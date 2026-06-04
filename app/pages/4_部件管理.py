# pages/4_部件管理.py
import streamlit as st
import pandas as pd
import logging
import sqlite3
from datetime import date
from utils.database import execute_query
from utils.auth import has_permission, log_user_action
from utils.ui import inject_global_css, page_header
from utils.nav import setup_sidebar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inject_global_css()

# --- 权限和登录检查 ---
if not st.session_state.get('logged_in', False):
    st.error("🔒 请先登录以访问此页面。")
    st.stop()

_ALLOWED_ROLES = {'超级管理员', '模具库管理员', '模具工'}
if st.session_state.get('user_role', '') not in _ALLOWED_ROLES:
    st.error("❌ 权限不足：您无法访问部件管理功能。")
    st.stop()

setup_sidebar("4_部件管理.py")
CAN_MANAGE = has_permission('manage_molds') or has_permission('manage_maintenance')

# --- 数据加载 ---
@st.cache_data(ttl=300)
def load_parts(mold_filter="", category_filter="全部", status_filter="全部", page=1, page_size=100):
    # 数据加载不再吞异常：DB 故障与编码缺陷均向上抛，由调用方
    # （show_parts_list）区分展示“加载失败”与“暂无数据”。
    where_clauses = []
    params = []

    if mold_filter:
        where_clauses.append("m.mold_code LIKE %s")
        params.append(f"%{mold_filter}%")
    if category_filter != "全部":
        where_clauses.append("c.category_name = %s")
        params.append(category_filter)
    if status_filter != "全部":
        where_clauses.append("ms.status_name = %s")
        params.append(status_filter)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    offset = max(page - 1, 0) * page_size
    query = """
    SELECT
        p.part_id,
        p.part_code     AS 部件编号,
        p.part_name     AS 部件名称,
        m.mold_code     AS 所属模具,
        c.category_name AS 部件类别,
        p.material      AS 材质,
        p.supplier      AS 供应商,
        p.installation_date AS 安装日期,
        p.lifespan_strokes  AS 设计寿命,
        ms.status_name  AS 状态,
        p.remarks       AS 备注
    FROM mold_parts p
    JOIN molds m ON p.mold_id = m.mold_id
    JOIN mold_part_categories c ON p.part_category_id = c.category_id
    LEFT JOIN mold_statuses ms ON p.current_status_id = ms.status_id
    {where_sql}
    ORDER BY p.created_at DESC
    LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = execute_query(query.format(where_sql=where_sql), params=tuple(params), fetch_all=True) or []
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def load_part_lookups():
    categories = execute_query(
        "SELECT category_id, category_name FROM mold_part_categories ORDER BY category_name",
        fetch_all=True
    ) or []
    molds = execute_query(
        "SELECT mold_id, mold_code, mold_name FROM molds ORDER BY mold_code",
        fetch_all=True
    ) or []
    statuses = execute_query(
        "SELECT status_id, status_name FROM mold_statuses ORDER BY status_id",
        fetch_all=True
    ) or []
    return categories, molds, statuses

# ===================== 主页面 =====================
def show():
    page_header("🔩", "部件管理", "部件台账 · 新增（含压边圈）")

    tab1, tab2 = st.tabs(["📋 部件列表", "➕ 新增部件"])

    with tab1:
        show_parts_list()

    with tab2:
        show_add_part_form()


# ===================== TAB1：部件列表 =====================
def show_parts_list():
    try:
        categories, _, statuses = load_part_lookups()
    except sqlite3.Error as e:
        logger.error(f"加载部件字典失败: {e}")
        st.error(f"❌ 数据加载失败：{e}")
        return
    cat_names = ["全部"] + [c['category_name'] for c in categories]
    st_names = ["全部"] + [s['status_name'] for s in statuses]

    c1, c2, c3 = st.columns([2, 2, 2])
    mold_filter = c1.text_input("按模具编号筛选", key="part_mold_filter")
    cat_filter = c2.selectbox("部件类别", cat_names, key="part_cat_filter")
    sta_filter = c3.selectbox("状态", st_names, key="part_sta_filter")

    page_col, size_col, _ = st.columns([1, 1, 4])
    page = page_col.number_input("页码", min_value=1, value=1, step=1, key="part_page")
    page_size = size_col.selectbox("每页", [50, 100, 200], index=1, key="part_page_size")

    col_r, _ = st.columns([1, 7])
    if col_r.button("🔄 刷新", key="refresh_parts"):
        st.cache_data.clear()
        st.rerun()

    try:
        df = load_parts(mold_filter, cat_filter, sta_filter, page, page_size)
    except sqlite3.Error as e:
        logger.error(f"加载部件列表失败: {e}")
        st.error(f"❌ 数据加载失败：{e}")
        return

    if df.empty:
        st.info("暂无符合条件的部件记录。")
        return

    display_cols = ['部件编号', '部件名称', '所属模具', '部件类别', '材质', '安装日期', '设计寿命', '状态']
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    st.caption(f"当前第 {page} 页，显示 {len(df)} 条记录")

    if CAN_MANAGE:
        with st.expander("🗑️ 删除部件", expanded=False):
            del_code = st.selectbox(
                "选择要删除的部件编号",
                ["（请选择）"] + df['部件编号'].dropna().tolist(),
                key="del_part_select"
            )
            if del_code != "（请选择）":
                if st.button("确认删除", type="primary", key="confirm_del_part"):
                    try:
                        execute_query(
                            "DELETE FROM mold_parts WHERE part_code = %s",
                            params=(del_code,), commit=True
                        )
                        log_user_action('DELETE_PART', 'mold_parts', del_code)
                        st.success(f"✅ 部件 {del_code} 已删除")
                        st.cache_data.clear()
                        st.rerun()
                    except sqlite3.Error as e:
                        logger.error(f"删除部件失败: {e}")
                        st.error(f"❌ 删除失败：{e}")


# ===================== TAB2：新增部件 =====================
def show_add_part_form():
    if not CAN_MANAGE:
        st.warning("🔒 您的角色没有新增部件的权限。")
        return

    try:
        categories, molds, statuses = load_part_lookups()
    except sqlite3.Error as e:
        logger.error(f"加载部件字典失败: {e}")
        st.error(f"❌ 数据加载失败：{e}")
        return

    if not molds:
        st.warning("⚠️ 系统中暂无模具，请先创建模具后再添加部件。")
        return

    with st.form("add_part_form", clear_on_submit=True):
        st.subheader("基本信息")
        c1, c2 = st.columns(2)

        mold_map = {f"{m['mold_code']} — {m['mold_name']}": m['mold_id'] for m in molds}
        selected_mold = c1.selectbox("所属模具 *", list(mold_map.keys()))

        cat_map = {c['category_name']: c['category_id'] for c in categories}
        if not cat_map:
            st.warning("⚠️ 暂无部件类别，请联系管理员在数据库中初始化 mold_part_categories 表。")
            st.form_submit_button("保存", disabled=True)
            return

        selected_cat = c2.selectbox("部件类别 *", list(cat_map.keys()))

        part_code = c1.text_input("部件编号", placeholder="PC-001（可留空自动生成）")
        part_name = c2.text_input("部件名称 *", placeholder="例：凸模镶块")

        c3, c4 = st.columns(2)
        material = c3.text_input("材质", placeholder="例：SKD11")
        supplier = c4.text_input("供应商")

        c5, c6 = st.columns(2)
        install_date = c5.date_input("安装日期", value=date.today())
        lifespan = c6.number_input("设计寿命（模次）", min_value=0, value=100000, step=10000)

        stat_map = {s['status_name']: s['status_id'] for s in statuses}
        init_status = st.selectbox(
            "初始状态",
            list(stat_map.keys()),
            index=list(stat_map.keys()).index('闲置') if '闲置' in stat_map else 0
        )
        remarks = st.text_area("备注", height=60)

        submitted = st.form_submit_button("➕ 新增部件", type="primary")

    if submitted:
        if not part_name.strip():
            st.error("❌ 部件名称不能为空")
            return

        # 检查编号唯一性（如果填写了）
        if part_code.strip():
            exists = execute_query(
                "SELECT part_id FROM mold_parts WHERE part_code = %s",
                params=(part_code.strip(),), fetch_one=True
            )
            if exists:
                st.error(f"❌ 部件编号 {part_code} 已存在")
                return

        try:
            insert_sql = """
            INSERT INTO mold_parts (
                mold_id, part_code, part_name, part_category_id,
                material, supplier, installation_date,
                lifespan_strokes, current_status_id, remarks,
                created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
            """
            execute_query(insert_sql, params=(
                mold_map[selected_mold],
                part_code.strip() or None,
                part_name.strip(),
                cat_map[selected_cat],
                material.strip() or None,
                supplier.strip() or None,
                install_date,
                lifespan if lifespan > 0 else None,
                stat_map.get(init_status),
                remarks.strip() or None
            ), commit=True)
            log_user_action('CREATE_PART', 'mold_parts', part_name.strip())
            st.success(f"✅ 部件「{part_name}」新增成功！")
            st.cache_data.clear()
        except sqlite3.Error as e:
            logger.error(f"新增部件失败: {e}")
            st.error(f"❌ 新增失败：{e}")


# --- 页面入口 ---
show()
