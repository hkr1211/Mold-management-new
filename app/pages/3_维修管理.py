# pages/maintenance_management.py
import streamlit as st
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, date
from utils.database import (
    execute_query, 
    get_db_connection,
    convert_numpy_types,
    get_all_molds,
    get_mold_by_id
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def get_maintenance_types():
    """获取维修保养类型"""
    query = "SELECT type_id, type_name, is_repair, description FROM maintenance_types ORDER BY type_name"
    try:
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        st.error(f"获取维修类型失败: {e}")
        return []

def get_maintenance_result_statuses():
    """获取维修结果状态"""
    query = "SELECT status_id, status_name, description FROM maintenance_result_statuses ORDER BY status_name"
    try:
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        st.error(f"获取维修结果状态失败: {e}")
        return []

def get_molds_needing_maintenance():
    """获取需要维修/保养的模具"""
    query = """
    SELECT 
        m.mold_id,
        m.mold_code,
        m.mold_name,
        m.accumulated_strokes,
        m.maintenance_cycle_strokes,
        m.theoretical_lifespan_strokes,
        mft.type_name as functional_type,
        ms.status_name as current_status,
        sl.location_name as current_location,
        CASE 
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes 
            THEN '需要保养'
            WHEN m.current_status_id IN (SELECT status_id FROM mold_statuses WHERE status_name IN ('待维修', '待保养'))
            THEN '等待维修/保养'
            WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9
            THEN '即将到期'
            ELSE '正常'
        END as maintenance_status,
        CASE 
            WHEN m.maintenance_cycle_strokes > 0 
            THEN m.accumulated_strokes - (m.accumulated_strokes / m.maintenance_cycle_strokes) * m.maintenance_cycle_strokes
            ELSE 0
        END as strokes_since_maintenance
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
    WHERE 
        (m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes)
        OR m.current_status_id IN (SELECT status_id FROM mold_statuses WHERE status_name IN ('待维修', '待保养'))
        OR (m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9)
    ORDER BY 
        CASE 
            WHEN ms.status_name IN ('待维修', '待保养') THEN 1
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes THEN 2
            ELSE 3
        END,
        m.mold_code
    """
    try:
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        st.error(f"获取维修需求失败: {e}")
        return []

def get_user_technicians():
    """获取模具工列表"""
    query = """
    SELECT u.user_id, u.full_name, u.username
    FROM users u 
    JOIN roles r ON u.role_id = r.role_id 
    WHERE r.role_name = '模具工' AND u.is_active = true
    ORDER BY u.full_name
    """
    try:
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        st.error(f"获取模具工列表失败: {e}")
        return []

def search_molds_for_maintenance(search_term=""):
    """搜索模具用于维修保养"""
    base_query = """
    SELECT 
        m.mold_id,
        m.mold_code,
        m.mold_name,
        mft.type_name as functional_type,
        ms.status_name as current_status,
        sl.location_name as current_location,
        m.accumulated_strokes,
        m.maintenance_cycle_strokes,
        m.theoretical_lifespan_strokes,
        CASE 
            WHEN m.maintenance_cycle_strokes > 0 
            THEN m.accumulated_strokes - (m.accumulated_strokes / m.maintenance_cycle_strokes) * m.maintenance_cycle_strokes
            ELSE m.accumulated_strokes
        END as strokes_since_maintenance
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
    """
    
    params = []
    if search_term.strip():
        base_query += " WHERE (m.mold_code ILIKE %s OR m.mold_name ILIKE %s)"
        search_param = f"%{search_term.strip()}%"
        params.extend([search_param, search_param])
    
    base_query += " ORDER BY m.mold_code LIMIT 50"
    
    try:
        return execute_query(base_query, params=tuple(params), fetch_all=True) or []
    except Exception as e:
        st.error(f"搜索模具失败: {e}")
        return []

# --- Main Functions ---

def show_maintenance_alerts():
    """显示维修保养预警"""
    st.subheader("⚠️ 维修保养预警")
    
    # 获取需要维修保养的模具
    maintenance_molds = get_molds_needing_maintenance()
    
    if not maintenance_molds:
        st.success("🎉 当前没有需要维修保养的模具")
        return
    
    # 按紧急程度分类显示
    urgent_molds = [m for m in maintenance_molds if m['maintenance_status'] == '等待维修/保养']
    overdue_molds = [m for m in maintenance_molds if m['maintenance_status'] == '需要保养']
    warning_molds = [m for m in maintenance_molds if m['maintenance_status'] == '即将到期']
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 紧急维修", len(urgent_molds))
    with col2:
        st.metric("🟡 超期保养", len(overdue_molds))
    with col3:
        st.metric("🟠 即将到期", len(warning_molds))
    with col4:
        st.metric("总计", len(maintenance_molds))
    
    # 详细列表
    if urgent_molds:
        st.markdown("### 🔴 紧急维修模具")
        for mold in urgent_molds:
            with st.expander(f"🚨 {mold['mold_code']} - {mold['mold_name']} ({mold['current_status']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**模具编号:** {mold['mold_code']}")
                    st.write(f"**模具名称:** {mold['mold_name']}")
                    st.write(f"**功能类型:** {mold['functional_type']}")
                    st.write(f"**当前状态:** {mold['current_status']}")
                with col2:
                    st.write(f"**存放位置:** {mold['current_location']}")
                    st.write(f"**累计冲次:** {mold['accumulated_strokes']:,}")
                    if  st.button(f"创建维修任务", key=f"create_urgent_{mold['mold_id']}"):
                        st.session_state.create_maintenance_mold_id = mold['mold_id']
                        st.session_state.maintenance_tab = "create_task"
                        st.rerun()
    
    if overdue_molds:
        st.markdown("### 🟡 超期保养模具")
        for mold in overdue_molds:
            with st.expander(f"⏰ {mold['mold_code']} - {mold['mold_name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**模具编号:** {mold['mold_code']}")
                    st.write(f"**模具名称:** {mold['mold_name']}")
                    st.write(f"**保养周期:** {mold['maintenance_cycle_strokes']:,} 冲次")
                with col2:
                    st.write(f"**累计冲次:** {mold['accumulated_strokes']:,}")
                    st.write(f"**距上次保养:** {mold['strokes_since_maintenance']:,} 冲次")
                    if  st.button(f"创建保养任务", key=f"create_overdue_{mold['mold_id']}"):
                        st.session_state.create_maintenance_mold_id = mold['mold_id']
                        st.session_state.maintenance_tab = "create_task"
                        st.rerun()
    
    if warning_molds:
        st.markdown("### 🟠 即将到期模具")
        for mold in warning_molds:
            with st.expander(f"⚡ {mold['mold_code']} - {mold['mold_name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**模具编号:** {mold['mold_code']}")
                    st.write(f"**理论寿命:** {mold['theoretical_lifespan_strokes']:,} 冲次")
                with col2:
                    st.write(f"**累计冲次:** {mold['accumulated_strokes']:,}")
                    usage_rate = (mold['accumulated_strokes'] / mold['theoretical_lifespan_strokes']) * 100
                    st.write(f"**使用率:** {usage_rate:.1f}%")
                    st.progress(min(usage_rate / 100, 1.0))

def create_maintenance_task():
    """创建维修保养任务"""
    st.subheader("🔧 创建维修保养任务")
    
    # 检查是否有预选的模具
    preselected_mold_id = st.session_state.get('create_maintenance_mold_id')
    
    if preselected_mold_id:
        # 显示预选模具信息
        mold_info = get_mold_by_id(preselected_mold_id)
        if mold_info:
            st.success(f"✅ 已选择模具: **{mold_info['mold_code']}** - {mold_info['mold_name']}")
            selected_mold_id = preselected_mold_id
        else:
            st.error("预选模具信息获取失败")
            return
    else:
        # 模具搜索和选择
        st.markdown("#### 🔍 搜索并选择模具")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("搜索模具", placeholder="输入模具编号或名称...")
        with col2:
            search_button =  st.button("🔍 搜索", type="primary")
        
        if search_button or search_term:
            search_results = search_molds_for_maintenance(search_term)
            
            if not search_results:
                st.warning("未找到匹配的模具")
                return
            
            # 模具选择
            mold_options = {}
            for mold in search_results:
                mold_options[mold['mold_id']] = f"{mold['mold_code']} - {mold['mold_name']} ({mold['current_status']})"
            
            selected_mold_id = st.selectbox(
                "选择模具:",
                options=list(mold_options.keys()),
                format_func=lambda x: mold_options[x],
                key="maintenance_mold_selector"
            )
        else:
            st.info("请搜索并选择要维修保养的模具")
            return
    
    if not selected_mold_id:
        return
    
    # 维修任务表单
    st.markdown("#### 📝 填写维修保养信息")
    
    # 获取维修类型和技术人员
    maintenance_types = get_maintenance_types()
    technicians = get_user_technicians()
    result_statuses = get_maintenance_result_statuses()
    
    with st.form("maintenance_task_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # 维修类型
            type_options = {}
            for mt in maintenance_types:
                type_options[mt['type_id']] = f"{mt['type_name']} ({'维修' if mt['is_repair'] else '保养'})"
            
            if type_options:
                maintenance_type_id = st.selectbox(
                    "维修/保养类型 *",
                    options=list(type_options.keys()),
                    format_func=lambda x: type_options[x]
                )
            else:
                st.error("无法获取维修类型选项")
                return
            
            # 执行人员
            tech_options = {}
            for tech in technicians:
                tech_options[tech['user_id']] = tech['full_name']
            
            if tech_options:
                maintained_by_id = st.selectbox(
                    "执行人员 *",
                    options=list(tech_options.keys()),
                    format_func=lambda x: tech_options[x]
                )
            else:
                st.error("无法获取模具工列表")
                return
            
            # 开始时间
            maintenance_start_date = st.date_input("开始日期 *", value=date.today())
            maintenance_start_time = st.time_input("开始时间 *", value=datetime.now().time())
        
        with col2:
            # 结束时间（可选）
            end_time_enabled = st.checkbox("任务已完成")
            if end_time_enabled:
                maintenance_end_date = st.date_input("结束日期", value=date.today())
                maintenance_end_time = st.time_input("结束时间", value=datetime.now().time())
                
                # 结果状态
                status_options = {}
                for status in result_statuses:
                    status_options[status['status_id']] = status['status_name']
                
                if status_options:
                    result_status_id = st.selectbox(
                        "结果状态 *",
                        options=list(status_options.keys()),
                        format_func=lambda x: status_options[x]
                    )
                else:
                    st.error("无法获取结果状态选项")
                    return
            else:
                maintenance_end_date = None
                maintenance_end_time = None
                result_status_id = None
            
            # 维修成本
            maintenance_cost = st.number_input(
                "维修成本 (元)", 
                min_value=0.0, 
                value=0.0, 
                step=0.01,
                format="%.2f"
            )
        
        # 问题描述
        problem_description = st.text_area(
            "问题描述", 
            placeholder="详细描述发现的问题或需要进行的保养内容...",
            height=100
        )
        
        # 处理措施
        actions_taken = st.text_area(
            "处理措施", 
            placeholder="详细描述采取的维修保养措施...",
            height=100
        )
        
        # 更换部件信息
        st.markdown("**更换部件信息** (可选)")
        col1, col2, col3 = st.columns(3)
        with col1:
            part_name = st.text_input("部件名称", placeholder="例如: 压边圈")
        with col2:
            part_code = st.text_input("部件编号", placeholder="例如: PC001")
        with col3:
            part_quantity = st.number_input("数量", min_value=0, value=0)
        
        # 备注
        notes = st.text_area("备注", placeholder="其他需要说明的信息...")
        
        # 提交按钮
        col1, col2 = st.columns([1, 3])
        with col1:
            submitted = st.form_submit_button("💾 保存任务", type="primary")
        with col2:
            if st.form_submit_button("🔄 清除选择"):
                if 'create_maintenance_mold_id' in st.session_state:
                    del st.session_state.create_maintenance_mold_id
                st.rerun()
        
        # 处理表单提交
        if submitted:
            # 验证必填字段
            if not all([maintenance_type_id, maintained_by_id, problem_description or actions_taken]):
                st.error("请填写所有必填字段")
                return
            
            # 构建时间戳
            start_datetime = datetime.combine(maintenance_start_date, maintenance_start_time)
            end_datetime = None
            if end_time_enabled and maintenance_end_date and maintenance_end_time:
                end_datetime = datetime.combine(maintenance_end_date, maintenance_end_time)
            
            # 构建更换部件信息
            replaced_parts_info = None
            if part_name and part_quantity > 0:
                replaced_parts_info = [{
                    "part_name": part_name,
                    "part_code": part_code or None,
                    "quantity": part_quantity
                }]
            
            # 保存维修记录
            success = save_maintenance_record(
                mold_id=selected_mold_id,
                maintenance_type_id=maintenance_type_id,
                maintained_by_id=maintained_by_id,
                start_timestamp=start_datetime,
                end_timestamp=end_datetime,
                problem_description=problem_description,
                actions_taken=actions_taken,
                maintenance_cost=maintenance_cost if maintenance_cost > 0 else None,
                result_status_id=result_status_id,
                replaced_parts_info=replaced_parts_info,
                notes=notes
            )
            
            if success:
                st.success("✅ 维修保养任务已保存！")
                st.balloons()
                
                # 清除选择状态
                if 'create_maintenance_mold_id' in st.session_state:
                    del st.session_state.create_maintenance_mold_id
                
                # 显示成功信息
                st.balloons()
                
                # 使用 rerun 刷新页面
                st.rerun()

def save_maintenance_record(mold_id, maintenance_type_id, maintained_by_id, start_timestamp,
                          end_timestamp=None, problem_description=None, actions_taken=None,
                          maintenance_cost=None, result_status_id=None, replaced_parts_info=None,
                          notes=None):
    """保存维修保养记录"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            
            # 如果没有提供结果状态，使用默认状态
            if not result_status_id:
                # 尝试多个可能的默认状态
                default_status_names = ['待开始', '进行中', '已创建', '待执行']
                
                for status_name in default_status_names:
                    cursor.execute(
                        "SELECT status_id FROM maintenance_result_statuses WHERE status_name = %s",
                        (status_name,)
                    )
                    default_status = cursor.fetchone()
                    if default_status:
                        result_status_id = default_status[0]
                        break
                
                if not result_status_id:
                    # 如果还是找不到，检查是否有任何状态记录
                    cursor.execute("SELECT status_id, status_name FROM maintenance_result_statuses LIMIT 5")
                    available_statuses = cursor.fetchall()
                    
                    if available_statuses:
                        # 使用第一个可用状态
                        result_status_id = available_statuses[0][0]
                        st.warning(f"使用默认状态: {available_statuses[0][1]}")
                    else:
                        st.error("❌ 数据库中没有维修状态数据！")
                        st.error("🔧 解决方案:")
                        st.code("python fix_maintenance_status.py")
                        st.info("或者联系管理员执行数据库初始化脚本")
                        return False
            
            # 插入维修记录
            insert_query = """
            INSERT INTO mold_maintenance_logs (
                mold_id, maintenance_type_id, maintained_by_id,
                maintenance_start_timestamp, maintenance_end_timestamp,
                problem_description, actions_taken, maintenance_cost,
                result_status_id, replaced_parts_info, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING log_id
            """
            
            # 将 replaced_parts_info 转换为 JSON 字符串
            import json
            replaced_parts_json = json.dumps(replaced_parts_info) if replaced_parts_info else None
            
            cursor.execute(insert_query, (
                mold_id, maintenance_type_id, maintained_by_id,
                start_timestamp, end_timestamp,
                problem_description, actions_taken, maintenance_cost,
                result_status_id, replaced_parts_json, notes
            ))
            
            log_id = cursor.fetchone()[0]
            
            # 如果任务已完成，更新模具状态
            if end_timestamp and result_status_id:
                # 获取结果状态名称
                cursor.execute(
                    "SELECT status_name FROM maintenance_result_statuses WHERE status_id = %s",
                    (result_status_id,)
                )
                status_result = cursor.fetchone()
                
                if status_result and status_result[0] in ['合格可用', '完成待检']:
                    # 更新模具状态为闲置
                    cursor.execute(
                        "SELECT status_id FROM mold_statuses WHERE status_name = '闲置'",
                    )
                    idle_status_result = cursor.fetchone()
                    
                    if idle_status_result:
                        cursor.execute(
                            "UPDATE molds SET current_status_id = %s, updated_at = %s WHERE mold_id = %s",
                            (idle_status_result[0], datetime.now(), mold_id)
                        )
            
            conn.commit()
            logging.info(f"Maintenance record created successfully: log_id={log_id}")
            return True
            
    except Exception as e:
        logging.error(f"Failed to save maintenance record: {e}", exc_info=True)
        st.error(f"保存维修记录失败: {e}")
        return False

def view_maintenance_tasks():
    """查看维修保养任务列表"""
    st.subheader("📋 维修保养任务列表")
    
    # 筛选条件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 维修类型筛选
        maintenance_types = get_maintenance_types()
        type_options = {0: "全部类型"}
        for mt in maintenance_types:
            type_options[mt['type_id']] = mt['type_name']
        
        selected_type_id = st.selectbox(
            "维修类型筛选",
            options=list(type_options.keys()),
            format_func=lambda x: type_options[x]
        )
    
    with col2:
        # 状态筛选
        result_statuses = get_maintenance_result_statuses()
        status_options = {0: "全部状态"}
        for rs in result_statuses:
            status_options[rs['status_id']] = rs['status_name']
        
        selected_status_id = st.selectbox(
            "状态筛选",
            options=list(status_options.keys()),
            format_func=lambda x: status_options[x]
        )
    
    with col3:
        # 时间范围筛选
        time_range = st.selectbox(
            "时间范围",
            options=['全部', '最近7天', '最近30天', '最近90天']
        )
    
    # 构建查询
    query = """
    SELECT 
        mml.log_id,
        m.mold_code,
        m.mold_name,
        mt.type_name as maintenance_type,
        mt.is_repair,
        u.full_name as maintained_by,
        mml.maintenance_start_timestamp,
        mml.maintenance_end_timestamp,
        mml.problem_description,
        mml.actions_taken,
        mml.maintenance_cost,
        mrs.status_name as result_status,
        mml.notes,
        mml.replaced_parts_info
    FROM mold_maintenance_logs mml
    JOIN molds m ON mml.mold_id = m.mold_id
    JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
    JOIN users u ON mml.maintained_by_id = u.user_id
    JOIN maintenance_result_statuses mrs ON mml.result_status_id = mrs.status_id
    WHERE 1=1
    """
    
    params = []
    
    # 添加筛选条件
    if selected_type_id != 0:
        query += " AND mml.maintenance_type_id = %s"
        params.append(selected_type_id)
    
    if selected_status_id != 0:
        query += " AND mml.result_status_id = %s"
        params.append(selected_status_id)
    
    # 时间范围筛选
    if time_range != '全部':
        days_map = {'最近7天': 7, '最近30天': 30, '最近90天': 90}
        days = days_map[time_range]
        query += " AND mml.maintenance_start_timestamp >= %s"
        params.append(datetime.now() - timedelta(days=days))
    
    query += " ORDER BY mml.maintenance_start_timestamp DESC LIMIT 100"
    
    # 执行查询
    try:
        maintenance_records = execute_query(query, params=tuple(params), fetch_all=True)
        
        if not maintenance_records:
            st.info("没有找到符合条件的维修保养记录")
            return
        
        # 统计信息
        total_records = len(maintenance_records)
        completed_records = len([r for r in maintenance_records if r['maintenance_end_timestamp']])
        in_progress_records = total_records - completed_records
        total_cost = sum([r['maintenance_cost'] or 0 for r in maintenance_records])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", total_records)
        with col2:
            st.metric("已完成", completed_records)
        with col3:
            st.metric("进行中", in_progress_records)
        with col4:
            st.metric("总成本", f"¥{total_cost:,.2f}")
        
        # 详细记录列表
        st.markdown("---")
        
        for record in maintenance_records:
            # 记录状态图标
            status_icons = {
                '进行中': '🔄',
                '完成待检': '⏳',
                '合格可用': '✅',
                '失败待查': '❌',
                '等待备件': '⏸️',
                '需要外协': '🔗'
            }
            
            status_icon = status_icons.get(record['result_status'], '📋')
            record_type = '🔧 维修' if record['is_repair'] else '🛠️ 保养'
            
            expander_title = f"{status_icon} {record_type} - {record['mold_code']} ({record['mold_name']}) - {record['maintained_by']} - {record['result_status']}"
            
            with st.expander(expander_title):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**记录ID:** {record['log_id']}")
                    st.write(f"**维修类型:** {record['maintenance_type']}")
                    st.write(f"**执行人:** {record['maintained_by']}")
                    st.write(f"**开始时间:** {record['maintenance_start_timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    
                    if record['maintenance_end_timestamp']:
                        st.write(f"**结束时间:** {record['maintenance_end_timestamp'].strftime('%Y-%m-%d %H:%M')}")
                        duration = record['maintenance_end_timestamp'] - record['maintenance_start_timestamp']
                        st.write(f"**耗时:** {duration}")
                    
                    if record['maintenance_cost']:
                        st.write(f"**维修成本:** ¥{record['maintenance_cost']:,.2f}")
                
                with col2:
                    st.write(f"**当前状态:** {record['result_status']}")
                    
                    # 操作按钮（针对进行中的任务）
                    if record['result_status'] in ['进行中', '等待备件']:
                        if  st.form_submit_button(f"✏️ 更新状态", key=f"update_{record['log_id']}"):
                            st.session_state.update_task_id = record['log_id']
                            st.session_state.maintenance_tab = "update_task"
                            st.rerun()
                
                # 详细信息
                if record['problem_description']:
                    st.markdown("**问题描述:**")
                    st.info(record['problem_description'])
                
                if record['actions_taken']:
                    st.markdown("**处理措施:**")
                    st.info(record['actions_taken'])
                
                # 更换部件信息
                if record['replaced_parts_info']:
                    try:
                        import json
                        parts_info = json.loads(record['replaced_parts_info'])
                        st.markdown("**更换部件:**")
                        for part in parts_info:
                            st.write(f"- {part.get('part_name', '')} ({part.get('part_code', '')}) x{part.get('quantity', 0)}")
                    except:
                        pass
                
                if record['notes']:
                    st.markdown("**备注:**")
                    st.info(record['notes'])
        
    except Exception as e:
        st.error(f"获取维修记录失败: {e}")
        logging.error(f"Failed to fetch maintenance records: {e}", exc_info=True)

def update_maintenance_task():
    """更新维修保养任务状态"""
    st.subheader("✏️ 更新维修保养任务")
    
    # 获取要更新的任务ID
    task_id = st.session_state.get('update_task_id')
    
    if not task_id:
        st.warning("请从任务列表选择要更新的任务")
        if  st.button("📋 返回任务列表"):
            st.session_state.maintenance_tab = "task_list"
            st.rerun()
        return
    
    # 获取任务详情
    query = """
    SELECT 
        mml.*,
        m.mold_code,
        m.mold_name,
        mt.type_name as maintenance_type,
        u.full_name as maintained_by,
        mrs.status_name as current_status
    FROM mold_maintenance_logs mml
    JOIN molds m ON mml.mold_id = m.mold_id
    JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
    JOIN users u ON mml.maintained_by_id = u.user_id
    JOIN maintenance_result_statuses mrs ON mml.result_status_id = mrs.status_id
    WHERE mml.log_id = %s
    """
    
    try:
        task_records = execute_query(query, params=(task_id,), fetch_all=True)
        if not task_records:
            st.error("未找到指定的维修任务")
            return
        
        task = task_records[0]
        
        # 显示任务基本信息
        st.info(f"**任务:** {task['maintenance_type']} - {task['mold_code']} ({task['mold_name']}) - 执行人: {task['maintained_by']}")
        
        # 更新表单
        result_statuses = get_maintenance_result_statuses()
        
        with st.form("update_task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # 结果状态
                status_options = {}
                for status in result_statuses:
                    status_options[status['status_id']] = status['status_name']
                
                current_status_id = task['result_status_id']
                new_status_id = st.selectbox(
                    "更新状态 *",
                    options=list(status_options.keys()),
                    format_func=lambda x: status_options[x],
                    index=list(status_options.keys()).index(current_status_id) if current_status_id in status_options else 0
                )
                
                # 完成时间
                if not task['maintenance_end_timestamp']:
                    task_completed = st.checkbox("标记为已完成")
                    if task_completed:
                        end_date = st.date_input("完成日期", value=date.today())
                        end_time = st.time_input("完成时间", value=datetime.now().time())
                    else:
                        end_date = None
                        end_time = None
                else:
                    st.write(f"**完成时间:** {task['maintenance_end_timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    task_completed = True
                    end_date = task['maintenance_end_timestamp'].date()
                    end_time = task['maintenance_end_timestamp'].time()
            
            with col2:
                # 维修成本
                current_cost = task['maintenance_cost'] or 0.0
                new_cost = st.number_input(
                    "维修成本 (元)",
                    min_value=0.0,
                    value=float(current_cost),
                    step=0.01,
                    format="%.2f"
                )
            
            # 更新处理措施
            current_actions = task['actions_taken'] or ""
            updated_actions = st.text_area(
                "处理措施",
                value=current_actions,
                height=100,
                help="补充或更新处理措施"
            )
            
            # 更新备注
            current_notes = task['notes'] or ""
            updated_notes = st.text_area(
                "备注",
                value=current_notes,
                height=80,
                help="补充或更新备注信息"
            )
            
            # 新增更换部件
            st.markdown("**新增更换部件** (可选)")
            col1, col2, col3 = st.columns(3)
            with col1:
                new_part_name = st.text_input("部件名称", placeholder="例如: 密封圈")
            with col2:
                new_part_code = st.text_input("部件编号", placeholder="例如: S001")
            with col3:
                new_part_quantity = st.number_input("数量", min_value=0, value=0)
            
            # 提交按钮
            col1, col2 = st.columns([1, 3])
            with col1:
                submitted = st.form_submit_button("💾 更新任务", type="primary")
            with col2:
                clear_and_return = st.form_submit_button("🔙 返回列表")
            
            # 处理表单提交
            if clear_and_return:
                st.session_state.maintenance_tab = "task_list"
                if 'update_task_id' in st.session_state:
                    del st.session_state.update_task_id
                st.rerun()
                
            if submitted:
                try:
                    with get_db_connection() as conn:
                        conn.autocommit = False
                        cursor = conn.cursor()
                        
                        # 构建更新查询
                        update_fields = []
                        update_params = []
                        
                        # 状态更新
                        if new_status_id != current_status_id:
                            update_fields.append("result_status_id = %s")
                            update_params.append(new_status_id)
                        
                        # 完成时间更新
                        if task_completed and end_date and end_time and not task['maintenance_end_timestamp']:
                            end_datetime = datetime.combine(end_date, end_time)
                            update_fields.append("maintenance_end_timestamp = %s")
                            update_params.append(end_datetime)
                        
                        # 成本更新
                        if new_cost != current_cost:
                            update_fields.append("maintenance_cost = %s")
                            update_params.append(new_cost if new_cost > 0 else None)
                        
                        # 处理措施更新
                        if updated_actions != current_actions:
                            update_fields.append("actions_taken = %s")
                            update_params.append(updated_actions)
                        
                        # 备注更新
                        if updated_notes != current_notes:
                            update_fields.append("notes = %s")
                            update_params.append(updated_notes)
                        
                        # 更换部件信息更新
                        if new_part_name and new_part_quantity > 0:
                            # 获取现有部件信息
                            current_parts = []
                            if task['replaced_parts_info']:
                                try:
                                    import json
                                    current_parts = json.loads(task['replaced_parts_info'])
                                except:
                                    current_parts = []
                            
                            # 添加新部件
                            new_part = {
                                "part_name": new_part_name,
                                "part_code": new_part_code or None,
                                "quantity": new_part_quantity
                            }
                            current_parts.append(new_part)
                            
                            import json
                            update_fields.append("replaced_parts_info = %s")
                            update_params.append(json.dumps(current_parts))
                        
                        # 执行更新
                        if update_fields:
                            update_query = f"""
                            UPDATE mold_maintenance_logs 
                            SET {', '.join(update_fields)}
                            WHERE log_id = %s
                            """
                            update_params.append(task_id)
                            
                            cursor.execute(update_query, tuple(update_params))
                            
                            # 如果任务完成且状态为合格，更新模具状态
                            if task_completed and new_status_id:
                                cursor.execute(
                                    "SELECT status_name FROM maintenance_result_statuses WHERE status_id = %s",
                                    (new_status_id,)
                                )
                                status_result = cursor.fetchone()
                                
                                if status_result and status_result[0] in ['合格可用']:
                                    cursor.execute(
                                        "SELECT status_id FROM mold_statuses WHERE status_name = '闲置'",
                                    )
                                    idle_status_result = cursor.fetchone()
                                    
                                    if idle_status_result:
                                        cursor.execute(
                                            "UPDATE molds SET current_status_id = %s, updated_at = %s WHERE mold_id = %s",
                                            (idle_status_result[0], datetime.now(), task['mold_id'])
                                        )
                            
                            conn.commit()
                            st.success("✅ 任务状态已更新！")
                            
                            # 清除更新状态
                            if 'update_task_id' in st.session_state:
                                del st.session_state.update_task_id
                            
                            st.balloons()
                        else:
                            st.info("没有检测到需要更新的内容")
                
                except Exception as e:
                    st.error(f"更新任务失败: {e}")
                    logging.error(f"Failed to update maintenance task: {e}", exc_info=True)
    
    except Exception as e:
        st.error(f"获取任务信息失败: {e}")
        logging.error(f"Failed to fetch task details: {e}", exc_info=True)

def maintenance_statistics():
    """维修保养统计分析"""
    st.subheader("📊 维修保养统计分析")
    
    # 时间范围选择
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("结束日期", value=date.today())
    
    try:
        # 总体统计
        stats_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN maintenance_end_timestamp IS NOT NULL THEN 1 END) as completed_records,
            COUNT(CASE WHEN mt.is_repair = true THEN 1 END) as repair_records,
            COUNT(CASE WHEN mt.is_repair = false THEN 1 END) as maintenance_records,
            COALESCE(SUM(maintenance_cost), 0) as total_cost,
            COALESCE(AVG(maintenance_cost), 0) as avg_cost
        FROM mold_maintenance_logs mml
        JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
        WHERE mml.maintenance_start_timestamp BETWEEN %s AND %s
        """
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        stats_result = execute_query(stats_query, params=(start_datetime, end_datetime), fetch_all=True)
        
        if stats_result:
            stats = stats_result[0]
            
            # 显示总体指标
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总记录数", stats['total_records'])
            with col2:
                st.metric("已完成", stats['completed_records'])
            with col3:
                st.metric("维修记录", stats['repair_records'])
            with col4:
                st.metric("保养记录", stats['maintenance_records'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总成本", f"¥{stats['total_cost']:,.2f}")
            with col2:
                st.metric("平均成本", f"¥{stats['avg_cost']:,.2f}")
        
        # 按类型统计
        st.markdown("### 📈 按维修类型统计")
        type_stats_query = """
        SELECT 
            mt.type_name,
            mt.is_repair,
            COUNT(*) as record_count,
            COALESCE(SUM(mml.maintenance_cost), 0) as total_cost,
            COALESCE(AVG(mml.maintenance_cost), 0) as avg_cost
        FROM mold_maintenance_logs mml
        JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
        WHERE mml.maintenance_start_timestamp BETWEEN %s AND %s
        GROUP BY mt.type_id, mt.type_name, mt.is_repair
        ORDER BY record_count DESC
        """
        
        type_stats = execute_query(type_stats_query, params=(start_datetime, end_datetime), fetch_all=True)
        
        if type_stats:
            df_type_stats = pd.DataFrame(type_stats)
            df_type_stats['类型'] = df_type_stats.apply(
                lambda row: f"{row['type_name']} ({'维修' if row['is_repair'] else '保养'})", 
                axis=1
            )
            
            # 使用streamlit的图表组件
            import plotly.express as px
            import plotly.graph_objects as go
            
            # 记录数量饼图
            col1, col2 = st.columns(2)
            
            with col1:
                fig_count = px.pie(
                    df_type_stats, 
                    values='record_count', 
                    names='类型',
                    title="维修保养记录数量分布"
                )
                st.plotly_chart(fig_count, use_container_width=True)
            
            with col2:
                fig_cost = px.pie(
                    df_type_stats, 
                    values='total_cost', 
                    names='类型',
                    title="维修保养成本分布"
                )
                st.plotly_chart(fig_cost, use_container_width=True)
            
            # 详细统计表
            st.dataframe(
                df_type_stats[['类型', 'record_count', 'total_cost', 'avg_cost']],
                column_config={
                    "类型": st.column_config.TextColumn("维修类型", width="medium"),
                    "record_count": st.column_config.NumberColumn("记录数量", width="small"),
                    "total_cost": st.column_config.NumberColumn("总成本 (元)", width="medium", format="¥%.2f"),
                    "avg_cost": st.column_config.NumberColumn("平均成本 (元)", width="medium", format="¥%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
        
        # 月度趋势分析
        st.markdown("### 📅 月度趋势分析")
        trend_query = """
        SELECT 
            DATE_TRUNC('month', mml.maintenance_start_timestamp) as month,
            COUNT(*) as record_count,
            COUNT(CASE WHEN mt.is_repair = true THEN 1 END) as repair_count,
            COUNT(CASE WHEN mt.is_repair = false THEN 1 END) as maintenance_count,
            COALESCE(SUM(mml.maintenance_cost), 0) as total_cost
        FROM mold_maintenance_logs mml
        JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
        WHERE mml.maintenance_start_timestamp >= %s - INTERVAL '6 months'
        GROUP BY DATE_TRUNC('month', mml.maintenance_start_timestamp)
        ORDER BY month
        """
        
        trend_stats = execute_query(trend_query, params=(start_datetime,), fetch_all=True)
        
        if trend_stats:
            df_trend = pd.DataFrame(trend_stats)
            df_trend['月份'] = pd.to_datetime(df_trend['month']).dt.strftime('%Y-%m')
            
            # 趋势图
            fig_trend = go.Figure()
            
            fig_trend.add_trace(go.Scatter(
                x=df_trend['月份'],
                y=df_trend['record_count'],
                mode='lines+markers',
                name='总记录数',
                line=dict(color='blue')
            ))
            
            fig_trend.add_trace(go.Scatter(
                x=df_trend['月份'],
                y=df_trend['repair_count'],
                mode='lines+markers',
                name='维修记录',
                line=dict(color='red')
            ))
            
            fig_trend.add_trace(go.Scatter(
                x=df_trend['月份'],
                y=df_trend['maintenance_count'],
                mode='lines+markers',
                name='保养记录',
                line=dict(color='green')
            ))
            
            fig_trend.update_layout(
                title="维修保养记录月度趋势",
                xaxis_title="月份",
                yaxis_title="记录数量",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # 成本趋势
            fig_cost_trend = px.bar(
                df_trend,
                x='月份',
                y='total_cost',
                title="维修保养成本月度趋势",
                color='total_cost',
                color_continuous_scale='Reds'
            )
            fig_cost_trend.update_layout(yaxis_title="成本 (元)")
            
            st.plotly_chart(fig_cost_trend, use_container_width=True)
    
    except Exception as e:
        st.error(f"获取统计数据失败: {e}")
        logging.error(f"Failed to fetch maintenance statistics: {e}", exc_info=True)

def show_system_check():
    """显示系统检查页面"""
    st.subheader("🔍 系统诊断")
    
    st.info("如果遇到 '无法获取默认维修状态' 错误，请运行以下检查")
    
    if  st.button("🔧 运行系统检查", type="primary"):
        with st.spinner("正在检查系统状态..."):
            # 检查维修结果状态
            try:
                result_statuses = get_maintenance_result_statuses()
                if result_statuses:
                    st.success(f"✅ 维修结果状态表正常 ({len(result_statuses)} 条记录)")
                    
                    # 显示状态列表
                    with st.expander("查看所有维修结果状态"):
                        for status in result_statuses:
                            st.write(f"- {status['status_name']}: {status.get('description', '无描述')}")
                else:
                    st.error("❌ 维修结果状态表为空")
                    show_fix_instructions()
            except Exception as e:
                st.error(f"❌ 检查维修结果状态失败: {e}")
                show_fix_instructions()
            
            # 检查维修类型
            try:
                maintenance_types = get_maintenance_types()
                if maintenance_types:
                    st.success(f"✅ 维修类型表正常 ({len(maintenance_types)} 条记录)")
                    
                    # 显示类型列表
                    with st.expander("查看所有维修类型"):
                        for mtype in maintenance_types:
                            type_desc = "维修" if mtype['is_repair'] else "保养"
                            st.write(f"- {mtype['type_name']} ({type_desc}): {mtype.get('description', '无描述')}")
                else:
                    st.error("❌ 维修类型表为空")
                    show_fix_instructions()
            except Exception as e:
                st.error(f"❌ 检查维修类型失败: {e}")
                show_fix_instructions()
            
            # 检查技术人员
            try:
                technicians = get_user_technicians()
                if technicians:
                    st.success(f"✅ 模具工账户正常 ({len(technicians)} 个)")
                else:
                    st.warning("⚠️ 没有找到模具工账户")
                    st.info("请确保数据库中有角色为 '模具工' 的用户")
            except Exception as e:
                st.error(f"❌ 检查技术人员失败: {e}")

def show_fix_instructions():
    """显示修复说明"""
    st.markdown("### 🛠️ 修复方法")
    
    st.markdown("**方法一：运行修复脚本**")
    st.code("""
# 下载并运行修复脚本
python fix_maintenance_status.py
    """)
    
    st.markdown("**方法二：手动执行SQL**")
    with st.expander("SQL修复脚本"):
        sql_fix = """
-- 插入维修结果状态
INSERT INTO maintenance_result_statuses (status_name, description) VALUES 
('待开始', '任务已创建，等待开始执行'),
('进行中', '维修保养工作正在进行'),
('完成待检', '维修保养完成，等待质量检验'),
('合格可用', '检验合格，可以正常使用'),
('失败待查', '维修失败，需要进一步分析'),
('等待备件', '等待备件到货后继续'),
('需要外协', '需要外部专业机构协助')
ON CONFLICT (status_name) DO NOTHING;

-- 插入维修类型
INSERT INTO maintenance_types (type_name, is_repair, description) VALUES 
('日常保养', FALSE, '日常清洁和基础维护'),
('定期保养', FALSE, '按周期进行的全面保养'),
('故障维修', TRUE, '设备故障后的修复工作'),
('精度维修', TRUE, '提高模具精度的维修')
ON CONFLICT (type_name) DO NOTHING;
        """
        st.code(sql_fix, language='sql')
    
    st.markdown("**方法三：重新运行部署脚本**")
    st.code("python deploy.py")
    
    st.warning("执行任何修复操作前，建议先备份数据库")

# --- Main Page Function ---

def show():
    """主函数 - 显示维修保养管理页面"""
    st.title("🔧 维修保养管理")
    
    # 权限检查
    user_role = st.session_state.get('user_role', '')
    if user_role not in ['超级管理员', '模具库管理员', '模具工']:
        st.warning("您没有权限访问此功能")
        return
    
    # 使用说明
    with st.expander("💡 使用说明", expanded=False):
        st.markdown("""
        ### 🔧 维修保养流程
        
        **1. 预警提醒**
        - 系统自动根据模具冲次和保养周期生成预警
        - 支持查看需要维修和保养的模具列表
        - 提供一键创建维修任务功能
        
        **2. 任务管理**
        - 创建维修保养任务，记录详细信息
        - 支持任务状态跟踪和更新
        - 记录维修成本和更换部件信息
        
        **3. 统计分析**
        - 提供维修保养的统计报表
        - 支持按类型、时间等维度分析
        - 协助制定维修保养策略
        
        ### 👥 角色权限
        - **模具库管理员**: 查看预警、创建任务、管理流程
        - **模具工**: 执行维修、更新任务状态、填写记录
        - **超级管理员**: 所有功能权限
        """)
    
    # 根据用户角色显示不同的页面组合
    if user_role == '模具工':
        # 模具工主要关注任务执行
        tab1, tab2, tab3 = st.tabs(["📋 我的任务", "🔧 创建任务", "📊 统计分析"])
        
        with tab1:
            view_maintenance_tasks()
        
        with tab2:
            create_maintenance_task()
        
        with tab3:
            maintenance_statistics()
    
    else:
        # 管理员有全部功能
        # 检查是否有跳转参数
        active_tab = st.session_state.get('maintenance_tab', 'alerts')
        
        if 'update_task_id' in st.session_state:
            active_tab = 'update_task'
        elif 'create_maintenance_mold_id' in st.session_state:
            active_tab = 'create_task'
        
        if active_tab == 'update_task':
            update_maintenance_task()
        elif active_tab == 'create_task':
            create_maintenance_task()
        elif active_tab == 'task_list':
            view_maintenance_tasks()
        elif active_tab == 'statistics':
            maintenance_statistics()
        elif active_tab == 'system_check':
            show_system_check()
        else:  # 默认显示预警页面
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚠️ 预警提醒", "🔧 创建任务", "📋 任务列表", "📊 统计分析", "🔍 系统诊断"])
            
            with tab1:
                show_maintenance_alerts()
            
            with tab2:
                create_maintenance_task()
            
            with tab3:
                view_maintenance_tasks()
            
            with tab4:
                maintenance_statistics()
                
            with tab5:
                show_system_check()
    
    # 清除导航状态
    if st.session_state.get('maintenance_tab') and st.session_state.get('maintenance_tab') != 'alerts':
        if  st.button("🏠 返回主页"):
            for key in ['maintenance_tab', 'create_maintenance_mold_id', 'update_task_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    # 用于独立测试的模拟会话状态
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = 1
        st.session_state['user_role'] = '模具库管理员'
        st.session_state['username'] = 'test_admin'
    
    show()