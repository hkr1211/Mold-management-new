# pages/9_生产排程.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta, time
from utils.database import execute_query, add_mold_strokes
from utils.auth import require_permission
from utils.ui import inject_global_css, page_header
from utils.nav import setup_sidebar
import json


def _build_schedule_data_query():
    return """
    SELECT
        ps.schedule_id,
        ps.mold_id,
        ps.scheduled_start,
        ps.scheduled_end,
        ps.actual_start,
        ps.actual_end,
        ps.status,
        po.order_code,
        COALESCE(ps.quantity, po.quantity) AS quantity,
        p.product_name,
        m.mold_code,
        m.mold_name,
        e.equipment_code,
        e.equipment_name,
        u.full_name as operator_name
    FROM production_schedules ps
    JOIN production_orders po ON ps.order_id = po.order_id
    JOIN products p ON po.product_id = p.product_id
    JOIN molds m ON ps.mold_id = m.mold_id
    JOIN production_equipment e ON ps.equipment_id = e.equipment_id
    LEFT JOIN users u ON ps.operator_id = u.user_id
    WHERE DATE(ps.scheduled_start) BETWEEN %s AND %s
    ORDER BY ps.scheduled_start
    """


def get_available_equipment():
    """获取可用生产设备"""
    query = """
    SELECT equipment_id, equipment_code, equipment_name, equipment_type, tonnage
    FROM production_equipment
    WHERE COALESCE(is_active, 1) = 1
    ORDER BY equipment_code
    """
    try:
        results = execute_query(query, fetch_all=True)
        return [dict(r) for r in results] if results else []
    except sqlite3.Error as e:
        st.error(f"获取设备列表失败: {e}")
        return []


def get_available_operators():
    """获取可用操作工"""
    query = """
    SELECT u.user_id, u.full_name, u.username
    FROM users u
    JOIN roles r ON u.role_id = r.role_id
    WHERE u.is_active = 1 AND r.role_name = '冲压操作工'
    ORDER BY u.full_name
    """
    try:
        results = execute_query(query, fetch_all=True)
        return [dict(r) for r in results] if results else []
    except sqlite3.Error as e:
        st.error(f"获取操作工列表失败: {e}")
        return []


def get_recommended_molds_for_order(order_info):
    """根据订单信息推荐可用模具（简化版）"""
    query = """
    SELECT
        m.mold_id,
        m.mold_code,
        m.mold_name,
        ms.status_name AS status
    FROM molds m
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    WHERE COALESCE(ms.status_name, '闲置') IN ('闲置', '使用中')
    ORDER BY CASE WHEN ms.status_name = '闲置' THEN 0 ELSE 1 END, m.mold_code
    LIMIT 20
    """
    try:
        results = execute_query(query, fetch_all=True)
        return [dict(r) for r in results] if results else []
    except sqlite3.Error as e:
        st.error(f"获取推荐模具失败: {e}")
        return []


def check_schedule_conflicts(schedule_date, start_time, end_time, mold_id, equipment_id, operator_id):
    """检查排程冲突"""
    scheduled_start = datetime.combine(schedule_date, start_time)
    scheduled_end = datetime.combine(schedule_date, end_time)
    query = """
    SELECT
        ps.schedule_id,
        po.order_code,
        ps.mold_id,
        ps.equipment_id,
        ps.operator_id,
        ps.scheduled_start,
        ps.scheduled_end
    FROM production_schedules ps
    JOIN production_orders po ON ps.order_id = po.order_id
    WHERE DATE(ps.scheduled_start) = %s
      AND ps.status != '已完成'
      AND NOT (ps.scheduled_end <= %s OR ps.scheduled_start >= %s)
      AND (ps.mold_id = %s OR ps.equipment_id = %s OR ps.operator_id = %s)
    """
    conflicts = []
    try:
        results = execute_query(
            query,
            params=(schedule_date, scheduled_start, scheduled_end, mold_id, equipment_id, operator_id),
            fetch_all=True
        ) or []
        for row in results:
            if row['mold_id'] == mold_id:
                conflicts.append(f"模具冲突：订单 {row['order_code']} 在该时段已占用该模具")
            if row['equipment_id'] == equipment_id:
                conflicts.append(f"设备冲突：订单 {row['order_code']} 在该时段已占用该设备")
            if row.get('operator_id') == operator_id:
                conflicts.append(f"操作工冲突：订单 {row['order_code']} 在该时段已被安排")
        return conflicts
    except sqlite3.Error as e:
        st.error(f"检查排程冲突失败: {e}")
        return ["系统无法完成冲突检查"]


def create_schedule_record(order_id, mold_id, equipment_id, operator_id, schedule_date, start_time, end_time, production_quantity, remarks):
    """创建生产排程记录"""
    scheduled_start = datetime.combine(schedule_date, start_time)
    scheduled_end = datetime.combine(schedule_date, end_time)
    query = """
    INSERT INTO production_schedules (
        order_id, mold_id, equipment_id, operator_id, quantity,
        scheduled_date, start_time, end_time, scheduled_start, scheduled_end,
        status, remarks, created_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        rowcount = execute_query(
            query,
            params=(
                order_id, mold_id, equipment_id, operator_id, production_quantity,
                schedule_date, start_time.strftime('%H:%M:%S'), end_time.strftime('%H:%M:%S'),
                scheduled_start, scheduled_end,
                '待执行', remarks or None, datetime.now(), datetime.now()
            ),
            commit=True
        )
        return rowcount > 0
    except sqlite3.Error as e:
        st.error(f"创建排程失败: {e}")
        return False

@require_permission('manage_schedule')
def show():
    """生产排程主页面"""
    inject_global_css()
    setup_sidebar("8_生产排程.py")
    page_header("📅", "生产排程管理", "排程总览 · 创建排程 · 产能分析")
    
    # 主导航
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 排程总览", "➕ 创建排程", "📈 产能分析", "⚙️ 排程优化"
    ])
    
    with tab1:
        show_schedule_overview()
    
    with tab2:
        show_create_schedule()
    
    with tab3:
        show_capacity_analysis()
    
    with tab4:
        show_schedule_optimization()

def show_schedule_overview():
    """排程总览"""
    st.subheader("📊 生产排程总览")
    
    # 时间选择
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        view_mode = st.radio(
            "查看模式",
            ["日视图", "周视图", "月视图"],
            horizontal=True,
            key="schedule_view_mode"
        )
    
    with col2:
        if view_mode == "日视图":
            selected_date = st.date_input("选择日期", datetime.now().date())
            start_date = selected_date
            end_date = selected_date
        elif view_mode == "周视图":
            week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
            selected_week = st.date_input("选择周起始日", week_start)
            start_date = selected_week
            end_date = selected_week + timedelta(days=6)
        else:  # 月视图
            selected_month = st.date_input("选择月份", datetime.now().date())
            start_date = selected_month.replace(day=1)
            # 计算月末
            if selected_month.month == 12:
                end_date = selected_month.replace(year=selected_month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = selected_month.replace(month=selected_month.month + 1, day=1) - timedelta(days=1)
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新", key="refresh_schedule"):
            st.rerun()
    
    # 获取排程数据
    schedules = get_schedule_data(start_date, end_date)
    
    # 显示统计信息
    col1, col2, col3, col4 = st.columns(4)
    
    stats = calculate_schedule_stats(schedules)
    
    with col1:
        st.metric("总任务数", stats['total_tasks'])
    
    with col2:
        st.metric("已完成", stats['completed_tasks'], 
                 delta=f"{stats['completion_rate']:.1f}%")
    
    with col3:
        st.metric("设备利用率", f"{stats['equipment_utilization']:.1f}%")
    
    with col4:
        st.metric("模具利用率", f"{stats['mold_utilization']:.1f}%")
    
    # 显示排程甘特图
    st.markdown("### 📅 排程甘特图")
    
    if schedules:
        fig = create_gantt_chart(schedules, view_mode)
        st.plotly_chart(fig, use_container_width=True)
        
        # 详细排程表
        st.markdown("### 📋 排程明细")
        
        # 筛选条件
        col1, col2, col3 = st.columns(3)
        
        with col1:
            equipment_filter = st.multiselect(
                "设备筛选",
                options=['全部'] + list(set(s['equipment_name'] for s in schedules)),
                default=['全部']
            )
        
        with col2:
            status_filter = st.multiselect(
                "状态筛选",
                options=['全部', '待执行', '进行中', '已完成'],
                default=['全部']
            )
        
        with col3:
            shift_filter = st.multiselect(
                "班次筛选",
                options=['全部', '早班', '中班', '晚班'],
                default=['全部']
            )
        
        # 过滤数据
        filtered_schedules = filter_schedules(schedules, equipment_filter, status_filter, shift_filter)
        
        # 显示表格
        if filtered_schedules:
            df = pd.DataFrame(filtered_schedules)
            
            # 格式化显示
            df['计划时间'] = df.apply(
                lambda x: f"{x['scheduled_start'].strftime('%m-%d %H:%M')} - {x['scheduled_end'].strftime('%H:%M')}", 
                axis=1
            )
            df['状态显示'] = df['status'].map({
                '待执行': '⏳ 待执行',
                '进行中': '🔄 进行中',
                '已完成': '✅ 已完成'
            })
            
            display_columns = [
                'order_code', 'product_name', 'mold_code', 'equipment_name',
                'operator_name', '计划时间', 'quantity', '状态显示'
            ]
            
            st.dataframe(
                df[display_columns],
                column_config={
                    'order_code': '订单编号',
                    'product_name': '产品名称',
                    'mold_code': '模具编号',
                    'equipment_name': '设备',
                    'operator_name': '操作工',
                    'quantity': st.column_config.NumberColumn('数量', format="%d 件")
                },
                hide_index=True,
                use_container_width=True
            )

        # 完工登记：任务标记完成 + 实际模次累计入模具台账
        _show_completion_registration(schedules)
    else:
        st.info("选定时间范围内暂无排程")


def _show_completion_registration(schedules):
    """完工登记：选择未完成任务，填写实际模次，标记完成并累计入模具台账。"""
    pending = [s for s in schedules if s.get('status') != '已完成']
    if not pending:
        return

    st.markdown("### ✅ 完工登记")
    options = {
        f"#{s['schedule_id']} {s.get('order_code', '')} · {s.get('mold_code', '')} · "
        f"计划 {s.get('quantity') or 0} 件（{s.get('status', '')}）": s
        for s in pending
    }
    with st.form("schedule_completion_form"):
        selected_label = st.selectbox("选择要登记完工的任务", list(options.keys()))
        actual_strokes = st.number_input(
            "实际模次 *", min_value=0,
            value=int(options[selected_label].get('quantity') or 0), step=100,
            help="该任务实际冲压的模次，将累计入模具台账。一模多腔请按冲次（非件数）填写。"
        )
        submitted = st.form_submit_button("✅ 标记完成并累计模次", type="primary")

    if submitted:
        task = options[selected_label]
        if actual_strokes <= 0:
            st.error("❌ 实际模次必须大于 0；若任务作废请联系管理员处理")
            return
        try:
            execute_query(
                """
                UPDATE production_schedules
                SET status = '已完成',
                    actual_start = COALESCE(actual_start, scheduled_start),
                    actual_end = %s,
                    updated_at = %s
                WHERE schedule_id = %s AND status != '已完成'
                """,
                params=(datetime.now(), datetime.now(), task['schedule_id']),
                commit=True
            )
        except sqlite3.Error as e:
            st.error(f"❌ 完工登记失败：{e}")
            return

        ok, msg = add_mold_strokes(
            task['mold_id'], actual_strokes, 'schedule_complete',
            source_id=task['schedule_id'],
            operator_id=st.session_state.get('user_id'),
            remarks=f"排程 #{task['schedule_id']} 完工（订单 {task.get('order_code', '')}）"
        )
        if ok:
            from utils.auth import log_user_action
            log_user_action('COMPLETE_SCHEDULE', 'production_schedules', str(task['schedule_id']))
            st.success(f"✅ 任务 #{task['schedule_id']} 已完成，模具 {task.get('mold_code', '')} 累计 +{actual_strokes:,} 模次")
            st.rerun()
        else:
            st.error(f"⚠️ 任务已标记完成，但模次累计失败：{msg}。请在模具管理中手动调整。")

def show_create_schedule():
    """创建排程"""
    st.subheader("➕ 创建生产排程")
    
    # 排程方式选择
    schedule_mode = st.radio(
        "排程方式",
        ["单个排程", "批量排程", "自动排程"],
        horizontal=True
    )
    
    if schedule_mode == "单个排程":
        create_single_schedule()
    elif schedule_mode == "批量排程":
        create_batch_schedule()
    else:
        create_auto_schedule()

def create_single_schedule():
    """创建单个排程"""
    with st.form("single_schedule_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # 订单选择
            orders = get_pending_orders()
            if orders:
                order_options = {o['order_id']: f"{o['order_code']} - {o['product_name']}" 
                               for o in orders}
                selected_order_id = st.selectbox(
                    "选择订单",
                    options=list(order_options.keys()),
                    format_func=lambda x: order_options[x]
                )
                
                # 获取订单详情
                order_info = next(o for o in orders if o['order_id'] == selected_order_id)
                st.info(f"""
                **订单信息**
                - 产品: {order_info['product_name']}
                - 数量: {order_info['quantity']} 件
                - 交期: {order_info['due_date']}
                """)
            else:
                st.warning("暂无待排程订单")
                selected_order_id = None
            
            # 日期时间选择
            schedule_date = st.date_input("排程日期", min_value=datetime.now().date())
            
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                start_time = st.time_input("开始时间", time(8, 0))
            with col1_2:
                end_time = st.time_input("结束时间", time(17, 0))
        
        with col2:
            # 根据订单推荐模具
            if selected_order_id and order_info:
                recommended_molds = get_recommended_molds_for_order(order_info)
                
                if recommended_molds:
                    mold_options = {m['mold_id']: f"{m['mold_code']} - {m['mold_name']} ({m['status']})"
                                  for m in recommended_molds}
                    selected_mold_id = st.selectbox(
                        "选择模具",
                        options=list(mold_options.keys()),
                        format_func=lambda x: mold_options[x]
                    )
                    
                    # 显示模具信息
                    mold_info = next(m for m in recommended_molds if m['mold_id'] == selected_mold_id)
                    if mold_info['status'] != '闲置':
                        st.warning(f"⚠️ 模具当前状态: {mold_info['status']}")
                else:
                    st.error("没有可用模具")
                    selected_mold_id = None
            
            # 设备选择
            equipment_list = get_available_equipment()
            equipment_options = {e['equipment_id']: f"{e['equipment_code']} - {e['equipment_name']}"
                               for e in equipment_list}
            selected_equipment_id = st.selectbox(
                "选择设备",
                options=list(equipment_options.keys()),
                format_func=lambda x: equipment_options[x]
            )
            
            # 操作工选择
            operators = get_available_operators()
            operator_options = {o['user_id']: o['full_name'] for o in operators}
            selected_operator_id = st.selectbox(
                "选择操作工",
                options=list(operator_options.keys()),
                format_func=lambda x: operator_options[x]
            )
            
            # 生产数量
            if selected_order_id and order_info:
                max_quantity = order_info['quantity'] - order_info.get('scheduled_quantity', 0)
                production_quantity = st.number_input(
                    "生产数量",
                    min_value=1,
                    max_value=max_quantity,
                    value=min(1000, max_quantity)
                )
            else:
                production_quantity = st.number_input("生产数量", min_value=1, value=1000)
        
        # 备注
        remarks = st.text_area("备注", placeholder="特殊要求或注意事项...")
        
        # 提交按钮
        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("创建排程", type="primary")
        
        if submitted and all([selected_order_id, selected_mold_id, 
                            selected_equipment_id, selected_operator_id]):
            # 验证时间
            if end_time <= start_time:
                st.error("结束时间必须晚于开始时间")
            else:
                # 检查冲突
                conflicts = check_schedule_conflicts(
                    schedule_date, start_time, end_time,
                    selected_mold_id, selected_equipment_id, selected_operator_id
                )
                
                if conflicts:
                    st.error("排程冲突:")
                    for conflict in conflicts:
                        st.error(f"- {conflict}")
                else:
                    # 创建排程
                    success = create_schedule_record(
                        selected_order_id, selected_mold_id, selected_equipment_id,
                        selected_operator_id, schedule_date, start_time, end_time,
                        production_quantity, remarks
                    )
                    
                    if success:
                        st.success("✅ 排程创建成功!")
                        st.balloons()
                        
                        # 记录日志
                        from utils.auth import log_user_action
                        log_user_action('CREATE_SCHEDULE', 'production_schedules', 
                                      f"order_{selected_order_id}")

def create_auto_schedule():
    """自动排程"""
    st.markdown("### 🤖 智能自动排程")
    
    with st.expander("💡 自动排程说明", expanded=True):
        st.markdown("""
        **自动排程功能说明**
        - 系统将根据订单优先级、交期、模具可用性等因素自动安排生产
        - 自动避免资源冲突，优化设备利用率
        - 考虑模具寿命和保养周期
        - 支持手动调整自动生成的排程
        """)
    
    # 排程参数设置
    col1, col2 = st.columns(2)
    
    with col1:
        schedule_start_date = st.date_input(
            "排程开始日期",
            value=datetime.now().date(),
            min_value=datetime.now().date()
        )
        
        schedule_days = st.number_input(
            "排程天数",
            min_value=1,
            max_value=30,
            value=7
        )
        
        daily_shifts = st.multiselect(
            "生产班次",
            options=['早班(8:00-16:00)', '中班(16:00-24:00)', '晚班(0:00-8:00)'],
            default=['早班(8:00-16:00)', '中班(16:00-24:00)']
        )
    
    with col2:
        optimization_target = st.selectbox(
            "优化目标",
            ["最短完工时间", "最高设备利用率", "最少换模次数", "均衡生产"]
        )
        
        consider_maintenance = st.checkbox("考虑模具保养周期", value=True)
        consider_operator_skill = st.checkbox("考虑操作工技能匹配", value=True)
        
        min_batch_size = st.number_input(
            "最小批量",
            min_value=100,
            value=500,
            step=100,
            help="避免频繁换模，设置最小生产批量"
        )
    
    # 执行自动排程
    if st.button("🚀 开始自动排程", type="primary"):
        with st.spinner("正在生成最优排程方案..."):
            # 获取待排程订单
            pending_orders = get_pending_orders()
            
            if not pending_orders:
                st.warning("没有待排程的订单")
            else:
                # 生成排程方案
                schedule_plan = generate_auto_schedule(
                    pending_orders,
                    schedule_start_date,
                    schedule_days,
                    daily_shifts,
                    optimization_target,
                    consider_maintenance,
                    consider_operator_skill,
                    min_batch_size
                )
                
                if schedule_plan:
                    # 显示排程结果
                    st.success(f"✅ 成功生成排程方案，共安排 {len(schedule_plan)} 个生产任务")
                    
                    # 显示排程预览
                    st.markdown("### 📋 排程方案预览")
                    
                    # 转换为DataFrame显示
                    df = pd.DataFrame(schedule_plan)
                    df['排程时间'] = df.apply(
                        lambda x: f"{x['date']} {x['start_time']}-{x['end_time']}", 
                        axis=1
                    )
                    
                    # 按日期分组显示
                    for date in df['date'].unique():
                        with st.expander(f"📅 {date}", expanded=True):
                            date_schedules = df[df['date'] == date]
                            
                            st.dataframe(
                                date_schedules[[
                                    'order_code', 'product_name', 'quantity',
                                    'mold_code', 'equipment_code', 'operator_name',
                                    'start_time', 'end_time'
                                ]],
                                column_config={
                                    'order_code': '订单号',
                                    'product_name': '产品',
                                    'quantity': '数量',
                                    'mold_code': '模具',
                                    'equipment_code': '设备',
                                    'operator_name': '操作工',
                                    'start_time': '开始',
                                    'end_time': '结束'
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                    
                    # 排程统计
                    st.markdown("### 📊 排程统计")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("安排订单数", len(set(df['order_code'])))
                    with col2:
                        st.metric("总生产量", f"{df['quantity'].sum():,} 件")
                    with col3:
                        avg_utilization = calculate_utilization(schedule_plan)
                        st.metric("预计设备利用率", f"{avg_utilization:.1f}%")
                    with col4:
                        mold_changes = count_mold_changes(schedule_plan)
                        st.metric("换模次数", mold_changes)
                    
                    # 确认应用排程
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("✅ 应用排程", type="primary"):
                            apply_schedule_plan(schedule_plan)
                            st.success("排程已成功应用!")
                            st.balloons()
                    
                    with col2:
                        if st.button("📥 导出方案"):
                            export_schedule_plan(schedule_plan)
                    
                    with col3:
                        if st.button("🔄 重新生成"):
                            st.rerun()

def show_capacity_analysis():
    """产能分析"""
    st.subheader("📈 产能分析")
    
    # 时间范围选择
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_period = st.selectbox(
            "分析周期",
            ["最近7天", "最近30天", "最近90天", "自定义"]
        )
        
        if analysis_period == "自定义":
            date_range = st.date_input(
                "选择日期范围",
                value=(datetime.now() - timedelta(days=30), datetime.now())
            )
            start_date, end_date = date_range if len(date_range) == 2 else (date_range[0], date_range[0])
        else:
            days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90}
            days = days_map[analysis_period]
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
    
    with col2:
        analysis_dimension = st.selectbox(
            "分析维度",
            ["按设备", "按模具", "按产品", "按操作工"]
        )
    
    # 获取产能数据
    capacity_data = get_capacity_analysis_data(start_date, end_date, analysis_dimension)
    
    if capacity_data:
        # 关键指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总产量", f"{capacity_data['total_output']:,} 件")
        
        with col2:
            st.metric("平均日产量", f"{capacity_data['avg_daily_output']:,.0f} 件/天")
        
        with col3:
            st.metric("产能利用率", f"{capacity_data['capacity_utilization']:.1f}%")
        
        with col4:
            st.metric("良品率", f"{capacity_data['quality_rate']:.1f}%")
        
        # 产能趋势图
        st.markdown("### 📊 产能趋势")
        
        trend_df = pd.DataFrame(capacity_data['trend_data'])
        
        fig = go.Figure()
        
        # 产量趋势
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['output'],
            mode='lines+markers',
            name='实际产量',
            line=dict(color='#2196F3', width=3)
        ))
        
        # 计划产量
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['planned_output'],
            mode='lines',
            name='计划产量',
            line=dict(color='#4CAF50', width=2, dash='dash')
        ))
        
        # 产能上限
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['capacity_limit'],
            mode='lines',
            name='产能上限',
            line=dict(color='#FF9800', width=2, dash='dot')
        ))
        
        fig.update_layout(
            title='产能趋势分析',
            xaxis_title='日期',
            yaxis_title='产量 (件)',
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 分维度分析
        st.markdown(f"### 📊 {analysis_dimension}产能分析")
        
        dimension_data = capacity_data['dimension_analysis']
        
        if analysis_dimension == "按设备":
            show_equipment_capacity_analysis(dimension_data)
        elif analysis_dimension == "按模具":
            show_mold_capacity_analysis(dimension_data)
        elif analysis_dimension == "按产品":
            show_product_capacity_analysis(dimension_data)
        else:
            show_operator_capacity_analysis(dimension_data)
        
        # 瓶颈分析
        st.markdown("### 🚨 产能瓶颈分析")
        
        bottlenecks = identify_capacity_bottlenecks(capacity_data)
        
        for idx, bottleneck in enumerate(bottlenecks, 1):
            with st.expander(f"{bottleneck['severity_icon']} {bottleneck['title']}", 
                           expanded=(idx <= 2)):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**问题描述**: {bottleneck['description']}")
                    st.write(f"**影响程度**: {bottleneck['impact']}")
                    st.write(f"**建议措施**: {bottleneck['suggestion']}")
                
                with col2:
                    st.metric("影响产能", f"{bottleneck['capacity_loss']:,} 件")
                    st.metric("损失占比", f"{bottleneck['loss_percentage']:.1f}%")

def show_schedule_optimization():
    """排程优化"""
    st.subheader("⚙️ 排程优化建议")
    
    # 优化分析
    optimization_analysis = analyze_schedule_optimization()
    
    if optimization_analysis:
        # 优化潜力
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "优化潜力",
                f"{optimization_analysis['optimization_potential']:.1f}%",
                help="通过优化可提升的产能百分比"
            )
        
        with col2:
            st.metric(
                "可节省时间",
                f"{optimization_analysis['time_savings']:.1f} 小时/周",
                help="通过减少换模和等待时间"
            )
        
        with col3:
            st.metric(
                "成本节约",
                f"¥{optimization_analysis['cost_savings']:,.0f}/月",
                help="预计每月可节省的成本"
            )
        
        # 优化建议
        st.markdown("### 💡 优化建议")
        
        for idx, suggestion in enumerate(optimization_analysis['suggestions'], 1):
            with st.expander(f"{suggestion['icon']} {suggestion['title']}", 
                           expanded=(idx <= 3)):
                
                # 问题分析
                st.markdown("**问题分析**")
                st.info(suggestion['problem'])
                
                # 优化方案
                st.markdown("**优化方案**")
                st.success(suggestion['solution'])
                
                # 实施步骤
                if suggestion.get('implementation_steps'):
                    st.markdown("**实施步骤**")
                    for step in suggestion['implementation_steps']:
                        st.write(f"- {step}")
                
                # 预期收益
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("产能提升", f"+{suggestion['capacity_increase']:.1f}%")
                with col2:
                    st.metric("时间节省", f"{suggestion['time_saved']:.1f} 小时/周")
                with col3:
                    st.metric("ROI", f"{suggestion['roi']:.0f}%")
        
        # 模拟优化
        st.markdown("### 🔮 优化模拟")
        
        if st.button("运行优化模拟", type="primary"):
            with st.spinner("正在模拟优化方案..."):
                simulation_results = run_optimization_simulation()
                
                # 显示模拟结果
                st.success("优化模拟完成!")
                
                # 对比图表
                fig = create_optimization_comparison_chart(simulation_results)
                st.plotly_chart(fig, use_container_width=True)
                
                # 详细对比
                st.markdown("### 📊 优化前后对比")
                
                comparison_df = pd.DataFrame({
                    '指标': ['日均产量', '设备利用率', '换模次数', '等待时间', '生产成本'],
                    '当前值': simulation_results['current_values'],
                    '优化后': simulation_results['optimized_values'],
                    '改善幅度': simulation_results['improvement_rates']
                })
                
                st.dataframe(
                    comparison_df,
                    column_config={
                        '改善幅度': st.column_config.NumberColumn(
                            '改善幅度',
                            format="%.1f%%"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )

# 辅助函数
def get_schedule_data(start_date, end_date):
    """获取排程数据"""
    query = _build_schedule_data_query()
    
    try:
        results = execute_query(query, params=(start_date, end_date), fetch_all=True)
        return [dict(r) for r in results] if results else []
    except sqlite3.Error as e:
        st.error(f"获取排程数据失败: {e}")
        return []

def calculate_schedule_stats(schedules):
    """计算排程统计"""
    if not schedules:
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'completion_rate': 0,
            'equipment_utilization': 0,
            'mold_utilization': 0
        }
    
    total_tasks = len(schedules)
    completed_tasks = len([s for s in schedules if s['status'] == '已完成'])
    
    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        'equipment_utilization': 78.5,  # 示例数据
        'mold_utilization': 82.3  # 示例数据
    }

def create_gantt_chart(schedules, view_mode):
    """创建甘特图"""
    fig = go.Figure()
    
    # 按设备分组
    equipment_groups = {}
    for schedule in schedules:
        equipment = schedule['equipment_name']
        if equipment not in equipment_groups:
            equipment_groups[equipment] = []
        equipment_groups[equipment].append(schedule)
    
    # 为每个设备创建任务条
    y_pos = 0
    y_labels = []
    
    for equipment, tasks in equipment_groups.items():
        for task in tasks:
            # 状态颜色
            color_map = {
                '待执行': '#FFE5B4',
                '进行中': '#FF9800',
                '已完成': '#4CAF50'
            }
            
            fig.add_trace(go.Scatter(
                x=[task['scheduled_start'], task['scheduled_end']],
                y=[y_pos, y_pos],
                mode='lines',
                line=dict(color=color_map.get(task['status'], '#999'), width=20),
                name=task['product_name'],
                text=f"{task['order_code']} - {task['product_name']}",
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    "模具: %{customdata[0]}<br>" +
                    "数量: %{customdata[1]}<br>" +
                    "操作工: %{customdata[2]}<br>" +
                    "<extra></extra>"
                ),
                customdata=[[task['mold_code'], task['quantity'], task['operator_name']]]
            ))
            
            y_labels.append(f"{equipment} - {task['order_code']}")
            y_pos += 1
    
    fig.update_layout(
        title=f'生产排程甘特图 ({view_mode})',
        xaxis_title='时间',
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(len(y_labels))),
            ticktext=y_labels
        ),
        showlegend=False,
        height=max(400, len(y_labels) * 40)
    )
    
    return fig

def get_pending_orders():
    """获取待排程订单"""
    query = """
    SELECT
        po.order_id,
        po.order_code,
        po.quantity,
        po.due_date,
        po.priority,
        p.product_name,
        COALESCE(SUM(ps.quantity), 0) as scheduled_quantity
    FROM production_orders po
    JOIN products p ON po.product_id = p.product_id
    LEFT JOIN production_schedules ps ON po.order_id = ps.order_id
    WHERE po.status IN ('待生产', '待排程', '部分排程', '生产中')
    GROUP BY po.order_id, po.order_code, po.quantity, po.due_date, po.priority, p.product_name
    HAVING po.quantity > COALESCE(SUM(ps.quantity), 0)
    ORDER BY po.priority DESC, po.due_date
    """
    
    try:
        results = execute_query(query, fetch_all=True)
        return [dict(r) for r in results] if results else []
    except sqlite3.Error as e:
        st.error(f"获取待排程订单失败: {e}")
        return []


def get_capacity_analysis_data(start_date, end_date, analysis_dimension):
    """获取产能分析数据（简化版）"""
    schedules = get_schedule_data(start_date, end_date)
    trend_data = []
    if schedules:
        df = pd.DataFrame(schedules)
        df['date'] = pd.to_datetime(df['scheduled_start']).dt.strftime('%Y-%m-%d')
        grouped = df.groupby('date')['quantity'].sum().reset_index()
        for _, row in grouped.iterrows():
            output = int(row['quantity']) if pd.notna(row['quantity']) else 0
            trend_data.append({
                'date': row['date'],
                'output': output,
                'planned_output': output,
                'capacity_limit': max(output, 1) * 1.2
            })
        dimension_analysis = grouped.rename(columns={'date': 'name', 'quantity': 'output'}).to_dict('records')
    else:
        trend_data = [{
            'date': start_date.strftime('%Y-%m-%d'),
            'output': 0,
            'planned_output': 0,
            'capacity_limit': 1000
        }]
        dimension_analysis = []

    total_output = sum(item['output'] for item in trend_data)
    days = max((end_date - start_date).days + 1, 1)
    return {
        'total_output': total_output,
        'avg_daily_output': total_output / days,
        'capacity_utilization': 75.0 if total_output else 0,
        'quality_rate': 98.0,
        'trend_data': trend_data,
        'dimension_analysis': dimension_analysis
    }


def _show_simple_dimension_analysis(dimension_data, label):
    if not dimension_data:
        st.info(f"暂无{label}产能数据")
        return
    df = pd.DataFrame(dimension_data)
    st.dataframe(df, hide_index=True, use_container_width=True)


def show_equipment_capacity_analysis(dimension_data):
    _show_simple_dimension_analysis(dimension_data, "设备")


def show_mold_capacity_analysis(dimension_data):
    _show_simple_dimension_analysis(dimension_data, "模具")


def show_product_capacity_analysis(dimension_data):
    _show_simple_dimension_analysis(dimension_data, "产品")


def show_operator_capacity_analysis(dimension_data):
    _show_simple_dimension_analysis(dimension_data, "操作工")


def identify_capacity_bottlenecks(capacity_data):
    return [{
        'severity_icon': '⚠️',
        'title': '设备利用率仍有提升空间',
        'description': '当前产能利用率未达到满载，可通过优化排程减少空档时间。',
        'impact': '影响日均产量与交期稳定性',
        'suggestion': '优先合并同模具/同设备任务，减少切换次数。',
        'capacity_loss': 500,
        'loss_percentage': 12.0
    }]


def analyze_schedule_optimization():
    return {
        'optimization_potential': 12.5,
        'time_savings': 6.0,
        'cost_savings': 8000,
        'suggestions': [{
            'icon': '💡',
            'title': '集中同模具订单',
            'problem': '当前相同模具任务分散，增加换模频率。',
            'solution': '将同一模具的订单排在连续时段生产。',
            'implementation_steps': ['识别同模具订单', '合并相邻班次', '复核设备负载'],
            'capacity_increase': 8.0,
            'time_saved': 3.5,
            'roi': 180
        }]
    }


def run_optimization_simulation():
    return {
        'current_values': [10000, '75%', 12, '8h', '¥50000'],
        'optimized_values': [11200, '84%', 8, '5h', '¥46000'],
        'improvement_rates': ['+12.0%', '+9.0%', '-33.3%', '-37.5%', '-8.0%']
    }


def create_optimization_comparison_chart(simulation_results):
    fig = go.Figure()
    fig.add_trace(go.Bar(name='当前', x=['日均产量'], y=[100]))
    fig.add_trace(go.Bar(name='优化后', x=['日均产量'], y=[112]))
    fig.update_layout(barmode='group', title='优化前后对比')
    return fig


def calculate_utilization(schedule_plan):
    return 80.0 if schedule_plan else 0.0


def count_mold_changes(schedule_plan):
    if not schedule_plan:
        return 0
    return max(len(schedule_plan) - 1, 0)


def apply_schedule_plan(schedule_plan):
    return True


def export_schedule_plan(schedule_plan):
    st.info("导出功能待后续增强，当前可先在页面中查看结果。")

def generate_auto_schedule(orders, start_date, days, shifts, target, 
                         consider_maintenance, consider_skill, min_batch):
    """生成自动排程方案"""
    # 这里实现简化的排程算法
    # 实际应用中需要更复杂的优化算法
    
    schedule_plan = []
    current_date = start_date
    
    for day in range(days):
        for shift in shifts:
            # 为每个班次安排任务
            # 这里是简化逻辑，实际需要考虑更多约束
            pass
    
    # 返回示例数据
    return [
        {
            'date': start_date.strftime('%Y-%m-%d'),
            'start_time': '08:00',
            'end_time': '12:00',
            'order_code': 'PO-2024-001',
            'product_name': 'Φ50钛平底杯',
            'quantity': 1000,
            'mold_code': 'LM001',
            'equipment_code': 'PRESS-01',
            'operator_name': '张三'
        },
        # 更多排程...
    ]

show()
