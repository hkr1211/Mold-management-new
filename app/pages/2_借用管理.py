# pages/loan_management.py - 改进版本
import streamlit as st
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, date
from utils.database import (
    execute_query, 
    get_db_connection,
    get_loan_statuses, 
    convert_numpy_types 
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def get_status_id_by_name(status_name, table_name="loan_statuses", name_column="status_name", id_column="status_id"):
    """Fetches the ID of a status by its name from a given status table."""
    query = f"SELECT {id_column} FROM {table_name} WHERE {name_column} = %s"
    try:
        result = execute_query(query, params=(status_name,), fetch_all=True)
        if result and len(result) > 0:
            return result[0][id_column]
        else:
            logging.error(f"Status '{status_name}' not found in table '{table_name}'.")
            st.error(f"系统错误：无法找到状态 '{status_name}'。请联系管理员。")
            return None
    except Exception as e:
        logging.error(f"Error fetching status ID for '{status_name}' from '{table_name}': {e}")
        st.error(f"数据库错误：获取状态ID失败。详情：{e}")
        return None

def search_available_molds(search_keyword=""):
    """搜索可用模具（状态为'闲置'）"""
    idle_status_id = get_status_id_by_name("闲置", table_name="mold_statuses")
    if not idle_status_id:
        return []

    # 构建搜索查询
    base_query = """
    SELECT 
        m.mold_id,
        m.mold_code,
        m.mold_name,
        mft.type_name as functional_type,
        ms.status_name as current_status,
        sl.location_name as current_location,
        COALESCE(m.theoretical_lifespan_strokes, 0) as theoretical_lifespan_strokes,
        COALESCE(m.accumulated_strokes, 0) as accumulated_strokes,
        COALESCE(m.remarks, '') as remarks
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
    WHERE m.current_status_id = %s
    """
    
    params = [idle_status_id]
    
    # 如果有搜索关键词，添加搜索条件
    if search_keyword.strip():
        base_query += " AND (m.mold_code ILIKE %s OR m.mold_name ILIKE %s OR mft.type_name ILIKE %s)"
        keyword_param = f"%{search_keyword.strip()}%"
        params.extend([keyword_param, keyword_param, keyword_param])
    
    base_query += " ORDER BY m.mold_code LIMIT 50"  # 限制结果数量提高性能
    
    try:
        results = execute_query(base_query, params=tuple(params), fetch_all=True)
        return results if results else []
    except Exception as e:
        logging.error(f"Error searching available molds: {e}")
        st.error(f"搜索可用模具时出错: {e}")
        return []

def get_mold_details(mold_id):
    """获取模具详细信息"""
    query = """
    SELECT 
        m.mold_id,
        m.mold_code,
        m.mold_name,
        mft.type_name as functional_type,
        COALESCE(m.theoretical_lifespan_strokes, 0) as theoretical_lifespan_strokes,
        COALESCE(m.accumulated_strokes, 0) as accumulated_strokes,
        sl.location_name as current_location,
        COALESCE(m.remarks, '') as remarks
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
    WHERE m.mold_id = %s
    """
    
    try:
        result = execute_query(query, params=(mold_id,), fetch_all=True)
        return result[0] if result else None
    except Exception as e:
        st.error(f"获取模具详情失败: {e}")
        return None

# --- Main Application Functions ---

def create_loan_application():
    """UI and logic for creating a new mold loan application with search functionality."""
    st.subheader("📝 新建借用申请")

    current_user_id = st.session_state.get('user_id')
    if not current_user_id:
        st.warning("请先登录系统。")
        return

    # 模具搜索区域
    st.markdown("#### 🔍 搜索并选择模具")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_keyword = st.text_input(
            "搜索模具", 
            placeholder="输入模具编号、名称或类型关键词...",
            help="支持模糊搜索模具编号、名称和功能类型"
        )
    
    with col2:
        search_button = st.button("🔍 搜索", type="primary")
    
    # 初始化搜索状态
    if 'mold_search_results' not in st.session_state:
        st.session_state.mold_search_results = []
    if 'selected_mold_id' not in st.session_state:
        st.session_state.selected_mold_id = None
    
    # 执行搜索
    if search_button or search_keyword:
        with st.spinner("搜索中..."):
            search_results = search_available_molds(search_keyword)
            st.session_state.mold_search_results = search_results
            
        if not search_results:
            if search_keyword:
                st.warning(f"未找到包含关键词 '{search_keyword}' 的可用模具")
            else:
                st.info("当前没有可供借用的闲置模具")
            return
        
        st.success(f"找到 {len(search_results)} 个匹配的可用模具")
    
    # 显示搜索结果
    if st.session_state.mold_search_results:
        st.markdown("#### 📋 搜索结果（点击选择模具）")
        
        # 创建可点击的模具列表
        for i, mold in enumerate(st.session_state.mold_search_results):
            # 计算使用率
            theoretical = mold.get('theoretical_lifespan_strokes', 0)
            accumulated = mold.get('accumulated_strokes', 0)
            usage_rate = (accumulated / theoretical * 100) if theoretical > 0 else 0
            
            # 使用expander展示模具信息
            with st.expander(
                f"🔧 {mold['mold_code']} - {mold['mold_name']} "
                f"({mold.get('functional_type', '未知类型')})",
                expanded=False
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**编号:** {mold['mold_code']}")
                    st.write(f"**名称:** {mold['mold_name']}")
                    st.write(f"**类型:** {mold.get('functional_type', '未知')}")
                    st.write(f"**位置:** {mold.get('current_location', '未知')}")
                
                with col2:
                    st.write(f"**理论寿命:** {theoretical:,} 冲次")
                    st.write(f"**已用冲次:** {accumulated:,} 冲次")
                    st.write(f"**使用率:** {usage_rate:.1f}%")
                    if usage_rate > 0:
                        st.progress(min(usage_rate / 100, 1.0))
                
                with col3:
                    if st.button(
                        "✅ 选择此模具", 
                        key=f"select_mold_{mold['mold_id']}", 
                        type="primary",
                        use_container_width=True
                    ):
                        st.session_state.selected_mold_id = mold['mold_id']
                        st.session_state.selected_mold_info = mold
                        st.success(f"已选择模具: {mold['mold_code']}")
                        st.rerun()
                
                if mold.get('remarks'):
                    st.info(f"**备注:** {mold['remarks']}")
    
    # 如果已选择模具，显示借用申请表单
    if st.session_state.get('selected_mold_id'):
        selected_mold = st.session_state.get('selected_mold_info')
        
        st.markdown("---")
        st.markdown("#### 📝 填写借用申请")
        
        # 显示选中的模具信息
        st.success(f"已选择模具: **{selected_mold['mold_code']}** - {selected_mold['mold_name']}")
        
        with st.form("loan_application_form"):
            # 显示模具基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**模具编号:** {selected_mold['mold_code']}")
                st.write(f"**模具名称:** {selected_mold['mold_name']}")
                st.write(f"**功能类型:** {selected_mold.get('functional_type', '未知')}")
            with col2:
                st.write(f"**当前位置:** {selected_mold.get('current_location', '未知')}")
                theoretical = selected_mold.get('theoretical_lifespan_strokes', 0)
                accumulated = selected_mold.get('accumulated_strokes', 0)
                if theoretical > 0:
                    remaining = theoretical - accumulated
                    st.write(f"**剩余寿命:** {remaining:,} 冲次")
                    usage_rate = accumulated / theoretical * 100
                    st.write(f"**当前使用率:** {usage_rate:.1f}%")
            
            st.markdown("---")
            
            # 借用申请表单
            col1, col2 = st.columns(2)
            
            with col1:
                min_return_date = date.today() + timedelta(days=1)
                expected_return_date = st.date_input(
                    "预计归还日期 *", 
                    min_value=min_return_date, 
                    value=min_return_date,
                    help="选择预计归还模具的日期"
                )
                
            with col2:
                destination_equipment = st.text_input(
                    "使用设备/目的地 *", 
                    placeholder="例如: PRESS-01、生产车间A等",
                    help="填写使用模具的设备或目的地"
                )
            
            # 生产任务信息（可选）
            col1, col2 = st.columns(2)
            with col1:
                production_order = st.text_input(
                    "生产订单号", 
                    placeholder="例如: PO-2024-001（可选）"
                )
            with col2:
                estimated_strokes = st.number_input(
                    "预计使用冲次", 
                    min_value=0, 
                    value=0,
                    help="预计本次使用的冲次数（可选）"
                )
            
            remarks = st.text_area(
                "备注", 
                placeholder="其他需要说明的信息...",
                height=100
            )
            
            # 提交和取消按钮
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                submitted = st.form_submit_button("📤 提交申请", type="primary")
            
            with col2:
                if st.form_submit_button("🔄 重新选择模具"):
                    st.session_state.selected_mold_id = None
                    st.session_state.selected_mold_info = None
                    st.rerun()

            # 处理表单提交
            if submitted:
                # 验证必填字段
                if not destination_equipment.strip():
                    st.error("请填写使用设备/目的地")
                elif not expected_return_date:
                    st.error("请选择预计归还日期")
                else:
                    # 提交借用申请
                    submit_loan_application(
                        mold_id=st.session_state.selected_mold_id,
                        applicant_id=current_user_id,
                        expected_return_date=expected_return_date,
                        destination_equipment=destination_equipment.strip(),
                        production_order=production_order.strip() if production_order.strip() else None,
                        estimated_strokes=estimated_strokes if estimated_strokes > 0 else None,
                        remarks=remarks.strip() if remarks.strip() else None
                    )

def submit_loan_application(mold_id, applicant_id, expected_return_date, destination_equipment, 
                          production_order=None, estimated_strokes=None, remarks=None):
    """提交借用申请"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # 获取待审批状态ID
            pending_status_id = get_status_id_by_name("待审批", table_name="loan_statuses")
            if not pending_status_id:
                st.error("系统配置错误：无法获取借用状态。")
                return

            # 再次验证模具状态（防止并发问题）
            cursor.execute(
                "SELECT current_status_id FROM molds WHERE mold_id = %s", 
                (mold_id,)
            )
            mold_status_result = cursor.fetchone()
            
            idle_status_id = get_status_id_by_name("闲置", table_name="mold_statuses")
            if not mold_status_result or mold_status_result[0] != idle_status_id:
                st.error("模具状态已改变，无法申请借用。请重新搜索选择。")
                conn.rollback()
                return

            # 构建完整的备注信息
            full_remarks = []
            if production_order:
                full_remarks.append(f"生产订单: {production_order}")
            if estimated_strokes:
                full_remarks.append(f"预计冲次: {estimated_strokes:,}")
            if remarks:
                full_remarks.append(f"备注: {remarks}")
            
            final_remarks = "; ".join(full_remarks) if full_remarks else None

            # 插入借用申请
            insert_query = """
            INSERT INTO mold_loan_records (
                mold_id, applicant_id, application_timestamp, 
                expected_return_timestamp, destination_equipment, 
                remarks, loan_status_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING loan_id
            """
            
            cursor.execute(insert_query, (
                mold_id, applicant_id, datetime.now(),
                expected_return_date, destination_equipment,
                final_remarks, pending_status_id
            ))
            
            loan_id = cursor.fetchone()[0]
            conn.commit()
            
            st.success("🎉 借用申请提交成功！")
            st.info(f"申请编号: {loan_id}，状态: 待审批")
            
            # 清除选择状态
            st.session_state.selected_mold_id = None
            st.session_state.selected_mold_info = None
            st.session_state.mold_search_results = []
            
            st.balloons()
            
            # 提示后续流程
            st.info("📋 申请已提交，请等待模具库管理员审批。您可以在'查看与管理申请'页面查看申请状态。")

    except Exception as e:
        logging.error(f"Loan application submission failed: {e}", exc_info=True)
        st.error(f"提交申请失败：{e}")

# 修复后的借用管理查询部分
# 替换 pages/loan_management.py 中的 view_loan_applications 函数

def view_loan_applications():
    """查看和管理借用申请"""
    st.subheader("🔍 查看与管理借用申请")

    current_user_id = st.session_state.get('user_id')
    current_user_role = st.session_state.get('user_role')

    if not current_user_id:
        st.warning("请先登录。")
        return

    # 状态筛选
    try:
        # 获取所有状态，包括调试信息
        all_statuses_result = execute_query("SELECT status_id, status_name FROM loan_statuses ORDER BY status_id", fetch_all=True)
        
        if not all_statuses_result:
            st.error("无法获取借用状态列表。请联系管理员检查数据库配置。")
            return
        
        # 显示调试信息（可选）
        with st.expander("🔧 调试信息", expanded=False):
            st.write("数据库中的所有借用状态:")
            for status in all_statuses_result:
                st.write(f"- ID: {status['status_id']}, 名称: '{status['status_name']}'")
            
        status_filter_options = {0: "全部状态"}
        for status in all_statuses_result:
            status_id = status['status_id'] if isinstance(status, dict) else status[0]
            status_name = status['status_name'] if isinstance(status, dict) else status[1]
            status_filter_options[status_id] = status_name
        
    except Exception as e:
        st.error(f"获取状态列表失败：{e}")
        return
    
    selected_status_id = st.selectbox(
        "按状态筛选:",
        options=list(status_filter_options.keys()),
        format_func=lambda x: status_filter_options[x],
        key="loan_status_filter"
    )

    # 获取借用申请数据 - 修复查询
    try:
        # 基础查询，确保字段存在
        query_base = """
        SELECT
            mlr.loan_id, 
            m.mold_code, 
            m.mold_name,
            u_applicant.full_name AS applicant_name, 
            mlr.application_timestamp,
            mlr.expected_return_timestamp, 
            mlr.loan_out_timestamp, 
            mlr.actual_return_timestamp,
            COALESCE(mlr.destination_equipment, '') as destination_equipment, 
            ls.status_name AS loan_status, 
            mlr.loan_status_id,
            COALESCE(u_approver.full_name, '') AS approver_name, 
            COALESCE(mlr.remarks, '') as remarks,
            m.mold_id
        FROM mold_loan_records mlr
        JOIN molds m ON mlr.mold_id = m.mold_id
        JOIN users u_applicant ON mlr.applicant_id = u_applicant.user_id
        JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
        LEFT JOIN users u_approver ON mlr.approver_id = u_approver.user_id
        """
        
        params = []
        if selected_status_id != 0:
            query_base += " WHERE mlr.loan_status_id = %s"
            params.append(selected_status_id)

        query_base += " ORDER BY mlr.application_timestamp DESC"
        
        # 执行查询并显示调试信息
        st.write(f"🔍 执行查询，状态ID筛选: {selected_status_id if selected_status_id != 0 else '全部'}")
        
        loan_apps_result = execute_query(query_base, params=tuple(params), fetch_all=True)
        
        # 显示查询结果统计
        if loan_apps_result:
            st.success(f"✅ 找到 {len(loan_apps_result)} 条记录")
        else:
            st.info("📋 没有找到符合条件的借用申请记录")
            
            # 如果筛选条件下没有记录，显示所有记录用于调试
            if selected_status_id != 0:
                st.write("🔧 显示所有记录用于调试:")
                all_records = execute_query(
                    query_base.replace(" WHERE mlr.loan_status_id = %s", ""), 
                    fetch_all=True
                )
                if all_records:
                    for record in all_records:
                        st.write(f"- 申请ID: {record.get('loan_id')}, 状态: {record.get('loan_status')} (ID: {record.get('loan_status_id')})")
            return

        # 显示统计信息
        total_apps = len(loan_apps_result)
        pending_count = len([app for app in loan_apps_result if app.get('loan_status') == '待审批'])
        approved_count = len([app for app in loan_apps_result if app.get('loan_status') in ['已批准', '已借出']])
        returned_count = len([app for app in loan_apps_result if app.get('loan_status') == '已归还'])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总申请数", total_apps)
        with col2:
            st.metric("待审批", pending_count)
        with col3:
            st.metric("已批准/借出", approved_count)
        with col4:
            st.metric("已归还", returned_count)

        # 显示申请列表
        status_emoji = {
            "待审批": "⏳", 
            "已批准": "✅", 
            "已批准待借出": "🎯",
            "已借出": "➡️",
            "已归还": "📥", 
            "已驳回": "❌", 
            "逾期": "⚠️" 
        }

        for record in loan_apps_result:
            record = convert_numpy_types(record) if isinstance(record, dict) else dict(record)
            
            app_id = record['loan_id']
            mold_id = record['mold_id']

            emoji = status_emoji.get(record['loan_status'], "📋")
            expander_title = f"{emoji} {record['mold_code']} ({record['mold_name']}) - 申请人: {record['applicant_name']} - 状态: {record['loan_status']}"
            
            with st.expander(expander_title):
                details_col, actions_col = st.columns([3, 1])

                with details_col:
                    st.write(f"**申请ID：** {app_id}")
                    st.write(f"**申请时间：** {record['application_timestamp'].strftime('%Y-%m-%d %H:%M') if pd.notna(record['application_timestamp']) else 'N/A'}")
                    if pd.notna(record.get('expected_return_timestamp')):
                        st.write(f"**预计归还：** {record['expected_return_timestamp'].strftime('%Y-%m-%d')}")
                    st.write(f"**使用设备：** {record['destination_equipment']}")
                    if pd.notna(record.get('loan_out_timestamp')):
                        st.write(f"**借出时间：** {record['loan_out_timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    if pd.notna(record.get('actual_return_timestamp')):
                        st.write(f"**归还时间：** {record['actual_return_timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    if record['approver_name']:
                        st.write(f"**审批人：** {record['approver_name']}")
                    if record['remarks']:
                        st.write(f"**申请备注：** {record['remarks']}")
                    
                    # 调试信息
                    st.write(f"🔧 **调试信息：** 状态ID: {record['loan_status_id']}, 状态名称: '{record['loan_status']}'")
                
                with actions_col:
                    # 权限定义
                    can_approve_reject = current_user_role in ['超级管理员', '模具库管理员']
                    can_manage_loan_flow = current_user_role in ['超级管理员', '模具库管理员']

                    if record['loan_status'] == '待审批' and can_approve_reject:
                        if st.button("✔️ 批准", key=f"approve_{app_id}", help="批准此申请"):
                            if approve_loan_application(app_id, mold_id, current_user_id):
                                st.rerun()
                        
                        rejection_reason = st.text_area("驳回理由:", key=f"reject_reason_{app_id}", height=100)
                        if st.button("❌ 驳回", key=f"reject_{app_id}", help="驳回此申请"):
                            if not rejection_reason.strip():
                                st.warning("请输入驳回理由。")
                            elif reject_loan_application(app_id, mold_id, current_user_id, rejection_reason):
                                st.rerun()

                    elif record['loan_status'] in ['已批准', '已批准待借出'] and can_manage_loan_flow:
                        if st.button("➡️ 确认借出", key=f"loan_out_{app_id}", help="确认模具已借出"):
                            if mark_as_loaned_out(app_id, mold_id, current_user_id):
                                st.rerun()
                    
                    elif record['loan_status'] == '已借出' and can_manage_loan_flow:
                        if st.button("📥 标记归还", key=f"return_{app_id}", help="标记模具已归还"):
                            if mark_as_returned(app_id, mold_id, current_user_id):
                                st.rerun()

    except Exception as e:
        logging.error(f"Failed to load loan applications: {e}")
        st.error(f"加载借用申请列表失败：{e}")
        st.exception(e)  # 显示详细错误用于调试

def _update_loan_and_mold_status(loan_id, mold_id,
                                 current_loan_status_name, target_loan_status_name,
                                 current_mold_status_name, target_mold_status_name,
                                 operator_user_id, 
                                 loan_timestamp_field=None,
                                 loan_operator_field=None,
                                 remarks_field=None, remarks_value=None):
    """Generic function to update loan and mold statuses within a transaction."""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # Get status IDs
            current_loan_status_id = get_status_id_by_name(current_loan_status_name, table_name="loan_statuses")
            target_loan_status_id = get_status_id_by_name(target_loan_status_name, table_name="loan_statuses")
            current_mold_status_id = get_status_id_by_name(current_mold_status_name, table_name="mold_statuses")
            target_mold_status_id = get_status_id_by_name(target_mold_status_name, table_name="mold_statuses")

            if not all([current_loan_status_id, target_loan_status_id, current_mold_status_id, target_mold_status_id]):
                st.error("系统配置错误：无法获取操作所需的状态ID。")
                conn.rollback()
                return False

            # Verify current loan application status
            cursor.execute("SELECT loan_status_id, mold_id FROM mold_loan_records WHERE loan_id = %s", (loan_id,))
            app_data = cursor.fetchone()
            if not app_data or app_data[0] != current_loan_status_id or app_data[1] != mold_id:
                st.warning(f"操作失败：申请状态不正确。请刷新页面。")
                conn.rollback()
                return False

            # Update loan application
            update_loan_q = "UPDATE mold_loan_records SET loan_status_id = %s"
            params_loan = [target_loan_status_id]
            
            now_timestamp = datetime.now()
            if loan_timestamp_field:
                update_loan_q += f", {loan_timestamp_field} = %s"
                params_loan.append(now_timestamp)
            if loan_operator_field:
                update_loan_q += f", {loan_operator_field} = %s"
                params_loan.append(operator_user_id)
            if remarks_field and remarks_value is not None:
                update_loan_q += f", {remarks_field} = %s"
                params_loan.append(remarks_value)
            
            update_loan_q += " WHERE loan_id = %s AND loan_status_id = %s"
            params_loan.extend([loan_id, current_loan_status_id])
            
            cursor.execute(update_loan_q, tuple(params_loan))
            if cursor.rowcount == 0:
                st.warning("操作失败：申请记录更新失败。")
                conn.rollback()
                return False

            # Update mold status
            update_mold_q = """
                UPDATE molds SET current_status_id = %s, updated_at = %s
                WHERE mold_id = %s AND current_status_id = %s
            """
            cursor.execute(update_mold_q, (target_mold_status_id, now_timestamp, mold_id, current_mold_status_id))

            conn.commit()
            st.success(f"操作成功：申请状态已更新为 {target_loan_status_name}。")
            return True

    except Exception as e:
        logging.error(f"Error during status update for loan {loan_id}: {e}", exc_info=True)
        st.error(f"操作失败：{e}")
        return False

def approve_loan_application(loan_id, mold_id, approver_user_id):
    return _update_loan_and_mold_status(
        loan_id, mold_id,
        current_loan_status_name="待审批", target_loan_status_name="已批准",
        current_mold_status_name="闲置", target_mold_status_name="已借出",
        operator_user_id=approver_user_id,
        loan_timestamp_field="approval_timestamp",
        loan_operator_field="approver_id"
    )

def reject_loan_application(loan_id, mold_id, approver_user_id, rejection_remarks):
    if not rejection_remarks or not rejection_remarks.strip():
        st.error("驳回操作必须填写驳回理由。")
        return False
    return _update_loan_and_mold_status(
        loan_id, mold_id,
        current_loan_status_name="待审批", target_loan_status_name="已驳回",
        current_mold_status_name="闲置", target_mold_status_name="闲置",
        operator_user_id=approver_user_id,
        loan_timestamp_field="approval_timestamp",
        loan_operator_field="approver_id",
        remarks_field="remarks", remarks_value=rejection_remarks
    )

def mark_as_loaned_out(loan_id, mold_id, operator_user_id):
    return _update_loan_and_mold_status(
        loan_id, mold_id,
        current_loan_status_name="已批准", target_loan_status_name="已借出",
        current_mold_status_name="已借出", target_mold_status_name="已借出",
        operator_user_id=operator_user_id,
        loan_timestamp_field="loan_out_timestamp"
    )

def mark_as_returned(loan_id, mold_id, operator_user_id):
    return _update_loan_and_mold_status(
        loan_id, mold_id,
        current_loan_status_name="已借出", target_loan_status_name="已归还",
        current_mold_status_name="已借出", target_mold_status_name="闲置",
        operator_user_id=operator_user_id,
        loan_timestamp_field="actual_return_timestamp"
    )

# --- Main page function ---
def show():
    """Main function to show loan management page"""
    st.title("🛠️ 模具借用管理")
    
    # Check user permissions
    user_role = st.session_state.get('user_role', '')
    if user_role not in ['超级管理员', '模具库管理员', '冲压操作工']:
        st.warning("您没有权限访问此功能")
        return
    
    # 添加使用说明
    with st.expander("💡 使用说明", expanded=False):
        st.markdown("""
        ### 📋 借用流程说明
        
        **1. 申请借用（冲压操作工）**
        - 在"新建借用申请"页面搜索需要的模具
        - 支持按模具编号、名称或类型关键词搜索
        - 选择模具后填写借用信息并提交申请
        
        **2. 审批管理（模具库管理员）**
        - 在"查看与管理申请"页面查看所有待审批申请
        - 可以批准或驳回申请，驳回需填写理由
        - 批准后可确认模具借出
        
        **3. 归还确认（模具库管理员）**
        - 模具使用完成后，确认归还操作
        - 系统自动更新模具状态为可用
        
        ### 🔍 搜索技巧
        - 输入模具编号：如 "LM001"
        - 输入模具名称：如 "钛杯"
        - 输入功能类型：如 "落料"、"引申"
        - 支持模糊匹配，不区分大小写
        """)
    
    # Page selection based on user role
    if user_role == '冲压操作工':
        # 冲压操作工看到申请和查看页面
        tab1, tab2 = st.tabs(["📝 新建借用申请", "📋 我的申请"])
        
        with tab1:
            create_loan_application()
        
        with tab2:
            view_loan_applications()
    else:
        # 管理员看到管理和申请页面
        tab1, tab2 = st.tabs(["📋 查看与管理申请", "📝 新建借用申请"])
        
        with tab1:
            view_loan_applications()
        
        with tab2:
            create_loan_application()