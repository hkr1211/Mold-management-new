# pages/1_模具管理.py
import streamlit as st
import pandas as pd
import plotly.express as px
import logging
import sqlite3
from datetime import date
from utils.database import (
    execute_query, get_all_molds, get_mold_statuses,
    get_storage_locations, get_functional_types
)
from utils.auth import has_permission, log_user_action, restore_session
from utils.ui import inject_global_css, page_header, download_csv_button
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
restore_session()  # 刷新页面后从令牌恢复登录态
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
def load_molds(keyword="", status_filter="全部", page=1, page_size=100):
    # 不再吞异常：DB 故障与编码缺陷一律上抛，由调用方（_load_or_stop）区分
    # 展示“加载失败”与“暂无数据”。
    # 统一模糊关键词：编号 / 名称 / 制作人 / 规格 任一命中即返回。
    where_clauses = []
    params = []

    if keyword:
        where_clauses.append(
            "(m.mold_code LIKE %s OR m.mold_name LIKE %s "
            "OR m.maker LIKE %s OR m.specification LIKE %s)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw])
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
        m.maker            AS 制作人,
        m.specification    AS 模具规格,
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

# --- 模具履历（一页式）查询与计算 ---

def _build_mold_loan_history_query():
    return """
    SELECT
        mlr.application_date AS 申请时间,
        u.full_name          AS 申请人,
        ls.status_name       AS 状态,
        mlr.expected_return_date AS 预计归还,
        mlr.actual_return_date   AS 实际归还,
        COALESCE(mlr.purpose, '') AS 用途
    FROM mold_loan_records mlr
    LEFT JOIN users u ON mlr.applicant_id = u.user_id
    LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
    WHERE mlr.mold_id = %s
    ORDER BY mlr.application_date DESC
    LIMIT 20
    """


def _build_mold_maintenance_history_query():
    return """
    SELECT
        ml.maintenance_start_timestamp AS 开始时间,
        ml.maintenance_end_timestamp   AS 结束时间,
        COALESCE(mt.type_name, '未分类') AS 类型,
        u.full_name                    AS 技师,
        mrs.status_name                AS 结果,
        ml.cost                        AS 费用,
        ml.strokes_at_maintenance      AS 当时模次
    FROM mold_maintenance_logs ml
    LEFT JOIN maintenance_types mt ON ml.maintenance_type_id = mt.type_id
    LEFT JOIN users u ON ml.technician_id = u.user_id
    LEFT JOIN maintenance_result_statuses mrs ON ml.result_status_id = mrs.status_id
    WHERE ml.mold_id = %s
    ORDER BY COALESCE(ml.maintenance_start_timestamp, ml.created_at) DESC
    LIMIT 20
    """


def _build_mold_parts_query():
    return """
    SELECT
        p.part_code      AS 部件编号,
        p.part_name      AS 部件名称,
        c.category_name  AS 类别,
        p.material       AS 材质,
        p.installation_date AS 安装日期,
        p.lifespan_strokes  AS 设计寿命,
        ms.status_name   AS 状态
    FROM mold_parts p
    LEFT JOIN mold_part_categories c ON p.part_category_id = c.category_id
    LEFT JOIN mold_statuses ms ON p.current_status_id = ms.status_id
    WHERE p.mold_id = %s
    ORDER BY p.part_code
    """


def _build_stroke_logs_query():
    return """
    SELECT
        sl.created_at    AS 时间,
        sl.strokes_added AS 模次,
        sl.source_type   AS 来源,
        sl.source_id     AS 单号,
        u.full_name      AS 操作人,
        sl.remarks       AS 备注
    FROM mold_stroke_logs sl
    LEFT JOIN users u ON sl.operator_id = u.user_id
    WHERE sl.mold_id = %s
    ORDER BY sl.created_at ASC, sl.stroke_log_id ASC
    LIMIT 200
    """


_STROKE_SOURCE_LABELS = {
    'loan_return': '借用归还',
    'schedule_complete': '排程完工',
    'manual_adjust': '手动调整',
}


def _stroke_curve_points(current_accumulated, logs):
    """由流水反推累计模次曲线。

    起点 = 当前累计 − 全部流水之和（即建账初始值），随后按时间逐笔累加。
    返回 (起点值, [(时间, 累计值), ...])，logs 须按时间升序。
    """
    current = int(current_accumulated or 0)
    total_delta = sum(int(l['模次'] or 0) for l in logs)
    base = current - total_delta
    points = []
    running = base
    for l in logs:
        running += int(l['模次'] or 0)
        points.append((l['时间'], running))
    return base, points


def _last_maintenance_strokes(mold_id):
    """最近一次已完成保养时的模次（与维修页预警口径一致）。"""
    row = execute_query(
        """
        SELECT MAX(COALESCE(strokes_at_maintenance, 0)) AS s
        FROM mold_maintenance_logs
        WHERE mold_id = %s AND maintenance_end_timestamp IS NOT NULL
        """,
        params=(mold_id,), fetch_one=True)
    return (row['s'] if row and row['s'] is not None else 0)


# --- 主页面 ---

tab1, tab2, tab3, tab4 = st.tabs(["📋 模具列表", "➕ 新增模具", "✏️ 编辑模具", "📜 模具履历"])

# ========== TAB1：模具列表 ==========
with tab1:
    col1, col2, col3 = st.columns([4, 2, 1])
    with col1:
        keyword = st.text_input(
            "🔍 关键词搜索", key="mold_keyword",
            placeholder="模糊匹配：编号 / 名称 / 制作人 / 规格（支持扫码枪）")
    with col2:
        statuses, _, _, _ = _load_or_stop(load_lookup_data)
        status_names = ["全部"] + [s['status_name'] for s in statuses]
        status_filter = st.selectbox("状态筛选", status_names, key="status_filter")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 搜索", type="primary", key="search_list", use_container_width=True):
            st.cache_data.clear()  # 搜索同时获取最新数据（替代原"刷新"）
            st.rerun()

    page_col, size_col, _ = st.columns([1, 1, 4])
    page = page_col.number_input("页码", min_value=1, value=1, step=1, key="mold_page")
    page_size = size_col.selectbox("每页", [50, 100, 200], index=1, key="mold_page_size")

    df = _load_or_stop(load_molds, keyword.strip(), status_filter, page, page_size)

    if df.empty:
        st.info("暂无符合条件的模具记录。")
    else:
        display_cols = ['模具编号', '模具名称', '功能类型', '当前状态', '存放位置',
                        '累计模次', '理论寿命', '保养周期', '负责人', '制作人', '模具规格']
        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
        )
        cap_col, dl_col = st.columns([3, 1])
        cap_col.caption(f"当前第 {page} 页，显示 {len(df)} 条记录")
        with dl_col:
            download_csv_button(df[display_cols], "模具列表", key="export_molds")

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
            maker = c2.text_input("制作人", placeholder="模具制作人/制作单位")
            specification = c1.text_input("模具规格", placeholder="具体尺寸，例：1200×800×650mm")

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
                        mold_code, mold_name, mold_drawing_number, maker, specification,
                        mold_functional_type_id, manufacturing_date,
                        theoretical_lifespan_strokes, maintenance_cycle_strokes, accumulated_strokes,
                        current_status_id, current_location_id, responsible_person_id,
                        remarks, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    """
                    try:
                        execute_query(insert_sql, params=(
                            mold_code.strip(), mold_name.strip(), drawing_number.strip() or None,
                            maker.strip() or None, specification.strip() or None, type_id, mfg_date,
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
                    new_maker = c2.text_input("制作人", value=mold_row.get('maker', '') or '')
                    new_specification = c1.text_input(
                        "模具规格", value=mold_row.get('specification', '') or '',
                        placeholder="具体尺寸，例：1200×800×650mm")

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
                            mold_name = %s, maker = %s, specification = %s,
                            current_status_id = %s, current_location_id = %s,
                            theoretical_lifespan_strokes = %s,
                            maintenance_cycle_strokes = %s, accumulated_strokes = %s,
                            responsible_person_id = %s, remarks = %s,
                            updated_at = NOW()
                        WHERE mold_code = %s
                        """
                        try:
                            execute_query(update_sql, params=(
                                new_name.strip(), new_maker.strip() or None,
                                new_specification.strip() or None,
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

# ========== TAB4：模具履历（一页式） ==========
with tab4:
    hist_kw = st.text_input("🔍 搜索模具（编号/名称）", key="hist_search",
                            placeholder="留空显示最近创建的模具")
    if hist_kw.strip():
        cand = _load_or_stop(
            execute_query,
            "SELECT mold_id, mold_code, mold_name FROM molds "
            "WHERE mold_code LIKE %s OR mold_name LIKE %s ORDER BY mold_code LIMIT 50",
            params=(f"%{hist_kw.strip()}%", f"%{hist_kw.strip()}%"), fetch_all=True) or []
    else:
        cand = _load_or_stop(
            execute_query,
            "SELECT mold_id, mold_code, mold_name FROM molds "
            "ORDER BY created_at DESC LIMIT 50", fetch_all=True) or []

    if not cand:
        st.info("未找到模具。")
    else:
        cand_map = {f"{c['mold_code']} — {c['mold_name']}": c['mold_id'] for c in cand}
        sel_label = st.selectbox("选择模具", list(cand_map.keys()), key="hist_select")
        hist_mold_id = cand_map[sel_label]

        mold = _load_or_stop(
            execute_query,
            """
            SELECT m.*, mft.type_name AS functional_type,
                   ms.status_name AS current_status,
                   sl.location_name AS current_location,
                   u.full_name AS responsible_person
            FROM molds m
            LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
            LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
            LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
            LEFT JOIN users u ON m.responsible_person_id = u.user_id
            WHERE m.mold_id = %s
            """,
            params=(hist_mold_id,), fetch_one=True)

        if not mold:
            st.error("模具不存在或已删除。")
        else:
            # ── 基本信息 ──
            st.markdown(f"### 🛠️ {mold['mold_code']} — {mold['mold_name']}")
            i1, i2, i3, i4 = st.columns(4)
            i1.markdown(f"**功能类型**：{mold.get('functional_type') or '—'}")
            i2.markdown(f"**当前状态**：{mold.get('current_status') or '—'}")
            i3.markdown(f"**存放位置**：{mold.get('current_location') or '—'}")
            i4.markdown(f"**负责人**：{mold.get('responsible_person') or '—'}")
            i1.markdown(f"**制作人**：{mold.get('maker') or '—'}")
            i2.markdown(f"**模具规格**：{mold.get('specification') or '—'}")
            i3.markdown(f"**图号**：{mold.get('mold_drawing_number') or '—'}")
            i4.markdown(f"**制造日期**：{mold.get('manufacturing_date') or '—'}")
            i1.markdown(f"**备注**：{mold.get('remarks') or '—'}")

            # ── 寿命与保养 ──
            st.markdown("#### 📊 寿命与保养")
            accumulated = int(mold.get('accumulated_strokes') or 0)
            lifespan = int(mold.get('theoretical_lifespan_strokes') or 0)
            cycle = int(mold.get('maintenance_cycle_strokes') or 0)
            since_maint = accumulated - _load_or_stop(_last_maintenance_strokes, hist_mold_id)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("累计模次", f"{accumulated:,}")
            m2.metric("理论寿命", f"{lifespan:,}" if lifespan else "未设置")
            m3.metric("距上次保养", f"{since_maint:,} 模次")
            if cycle:
                m4.metric("保养周期", f"{cycle:,}",
                          delta=("⚠️ 已到期" if since_maint >= cycle else "正常"),
                          delta_color=("inverse" if since_maint >= cycle else "normal"))
            else:
                m4.metric("保养周期", "未设置")

            if lifespan > 0:
                usage = min(accumulated / lifespan, 1.0)
                st.progress(usage)
                st.caption(f"寿命使用率：{usage * 100:.1f}%")

            # ── 模次曲线 ──
            stroke_logs = _load_or_stop(
                execute_query, _build_stroke_logs_query(),
                params=(hist_mold_id,), fetch_all=True) or []
            if stroke_logs:
                base, points = _stroke_curve_points(accumulated, stroke_logs)
                curve_df = pd.DataFrame(points, columns=['时间', '累计模次'])
                fig = px.line(curve_df, x='时间', y='累计模次', markers=True,
                              title=f"累计模次走势（建账初始 {base:,}）")
                fig.update_layout(height=320)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无模次流水（借用归还/排程完工后自动生成）。")

            # ── 历史记录 ──
            h1, h2 = st.columns(2)
            with h1:
                st.markdown("#### 📋 借用历史（近20条）")
                loans = _load_or_stop(
                    execute_query, _build_mold_loan_history_query(),
                    params=(hist_mold_id,), fetch_all=True) or []
                if loans:
                    st.dataframe(pd.DataFrame(loans), hide_index=True,
                                 use_container_width=True)
                else:
                    st.caption("暂无借用记录")
            with h2:
                st.markdown("#### 🔧 维修历史（近20条）")
                maints = _load_or_stop(
                    execute_query, _build_mold_maintenance_history_query(),
                    params=(hist_mold_id,), fetch_all=True) or []
                if maints:
                    st.dataframe(pd.DataFrame(maints), hide_index=True,
                                 use_container_width=True)
                else:
                    st.caption("暂无维修记录")

            st.markdown("#### 🔩 部件清单")
            parts = _load_or_stop(
                execute_query, _build_mold_parts_query(),
                params=(hist_mold_id,), fetch_all=True) or []
            if parts:
                st.dataframe(pd.DataFrame(parts), hide_index=True,
                             use_container_width=True)
            else:
                st.caption("暂无部件记录")

            with st.expander("📑 模次流水明细"):
                if stroke_logs:
                    flow_df = pd.DataFrame(stroke_logs)
                    flow_df['来源'] = flow_df['来源'].map(
                        lambda s: _STROKE_SOURCE_LABELS.get(s, s))
                    st.dataframe(flow_df.iloc[::-1], hide_index=True,
                                 use_container_width=True)
                else:
                    st.caption("暂无流水")
