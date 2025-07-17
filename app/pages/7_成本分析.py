# pages/8_成本分析.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.database import execute_query
from utils.auth import require_permission

@require_permission('view_reports')
def show():
    """成本分析主页面"""
    st.title("💰 成本分析仪表板")
    
    # 添加自定义样式
    st.markdown("""
    <style>
        .cost-metric {
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8787 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }
        .saving-metric {
            background: linear-gradient(135deg, #4ECDC4 0%, #6EE7E0 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 时间范围选择
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        time_range = st.selectbox(
            "时间范围",
            ["本月", "上月", "本季度", "本年", "自定义"],
            key="cost_time_range"
        )
    
    with col2:
        if time_range == "自定义":
            date_range = st.date_input(
                "选择日期范围",
                value=(datetime.now() - timedelta(days=30), datetime.now()),
                key="custom_date_range"
            )
            start_date, end_date = date_range if len(date_range) == 2 else (date_range[0], date_range[0])
        else:
            start_date, end_date = get_date_range(time_range)
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新数据", key="refresh_cost"):
            st.rerun()
    
    # 获取成本数据
    cost_data = get_cost_summary(start_date, end_date)
    
    # 显示关键指标
    st.markdown("### 📊 成本概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_cost = cost_data['total_cost']
        st.metric(
            "总成本",
            f"¥{total_cost:,.2f}",
            delta=f"{cost_data['cost_change']:.1f}%",
            delta_color="inverse"
        )
    
    with col2:
        maintenance_cost = cost_data['maintenance_cost']
        st.metric(
            "维修成本",
            f"¥{maintenance_cost:,.2f}",
            delta=f"{cost_data['maintenance_change']:.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        downtime_cost = cost_data['downtime_cost']
        st.metric(
            "停机损失",
            f"¥{downtime_cost:,.2f}",
            delta=f"{cost_data['downtime_change']:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        avg_cost_per_mold = cost_data['avg_cost_per_mold']
        st.metric(
            "单模具平均成本",
            f"¥{avg_cost_per_mold:,.2f}",
            delta=f"{cost_data['avg_change']:.1f}%",
            delta_color="inverse"
        )
    
    # 详细分析标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 成本趋势", "🔧 模具成本明细", "⏱️ 停机分析", "💡 成本优化建议"
    ])
    
    with tab1:
        show_cost_trends(start_date, end_date)
    
    with tab2:
        show_mold_cost_details(start_date, end_date)
    
    with tab3:
        show_downtime_analysis(start_date, end_date)
    
    with tab4:
        show_cost_optimization_suggestions()

def show_cost_trends(start_date, end_date):
    """显示成本趋势"""
    st.subheader("📈 成本趋势分析")
    
    # 获取趋势数据
    trend_data = get_cost_trend_data(start_date, end_date)
    
    if trend_data:
        df = pd.DataFrame(trend_data)
        
        # 成本趋势图
        fig = go.Figure()
        
        # 添加各类成本趋势线
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['maintenance_cost'],
            mode='lines+markers',
            name='维修成本',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['downtime_cost'],
            mode='lines+markers',
            name='停机损失',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['total_cost'],
            mode='lines+markers',
            name='总成本',
            line=dict(color='#764BA2', width=3, dash='dash'),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title='成本趋势图',
            xaxis_title='日期',
            yaxis_title='成本 (元)',
            hovermode='x unified',
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 成本构成饼图
        col1, col2 = st.columns(2)
        
        with col1:
            # 当期成本构成
            current_composition = get_cost_composition(start_date, end_date)
            
            fig_pie = px.pie(
                values=current_composition['values'],
                names=current_composition['names'],
                title='成本构成分析',
                color_discrete_map={
                    '维修成本': '#FF6B6B',
                    '停机损失': '#4ECDC4',
                    '材料成本': '#FFE66D',
                    '其他成本': '#95A99C'
                }
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 成本占比变化
            st.markdown("**成本占比变化**")
            
            for item in current_composition['changes']:
                change_icon = "📈" if item['change'] > 0 else "📉"
                color = "red" if item['change'] > 0 else "green"
                
                st.markdown(
                    f"{change_icon} **{item['name']}**: "
                    f"{item['percentage']:.1f}% "
                    f"(<span style='color:{color}'>{item['change']:+.1f}%</span>)",
                    unsafe_allow_html=True
                )
    else:
        st.info("暂无成本趋势数据")

def show_mold_cost_details(start_date, end_date):
    """显示模具成本明细"""
    st.subheader("🔧 模具成本明细")
    
    # 筛选条件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cost_type_filter = st.selectbox(
            "成本类型",
            ["全部", "维修成本", "停机损失", "材料成本"],
            key="cost_type_filter"
        )
    
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["总成本降序", "总成本升序", "使用率降序", "维修次数降序"],
            key="cost_sort"
        )
    
    with col3:
        top_n = st.number_input("显示前N个", min_value=5, max_value=50, value=10)
    
    # 获取模具成本数据
    mold_costs = get_mold_cost_details(start_date, end_date, cost_type_filter, sort_by, top_n)
    
    if mold_costs:
        # 创建成本排行图
        df = pd.DataFrame(mold_costs)
        
        fig = px.bar(
            df,
            x='total_cost',
            y='mold_name',
            orientation='h',
            color='cost_per_use',
            color_continuous_scale='Reds',
            title=f'模具成本排行 (前{top_n}名)',
            labels={
                'total_cost': '总成本 (元)',
                'mold_name': '模具名称',
                'cost_per_use': '单次使用成本'
            }
        )
        
        fig.update_layout(height=400 + len(mold_costs) * 30)
        st.plotly_chart(fig, use_container_width=True)
        
        # 详细表格
        st.markdown("### 📋 成本明细表")
        
        # 格式化数据
        df['维修成本'] = df['maintenance_cost'].apply(lambda x: f"¥{x:,.2f}")
        df['停机损失'] = df['downtime_cost'].apply(lambda x: f"¥{x:,.2f}")
        df['总成本'] = df['total_cost'].apply(lambda x: f"¥{x:,.2f}")
        df['单次成本'] = df['cost_per_use'].apply(lambda x: f"¥{x:,.2f}")
        df['成本占比'] = df['cost_percentage'].apply(lambda x: f"{x:.1f}%")
        
        # 选择显示列
        display_columns = [
            'mold_code', 'mold_name', '维修成本', '停机损失', 
            '总成本', '单次成本', '成本占比', 'maintenance_count'
        ]
        
        st.dataframe(
            df[display_columns],
            column_config={
                'mold_code': '模具编号',
                'mold_name': '模具名称',
                'maintenance_count': st.column_config.NumberColumn(
                    '维修次数',
                    format="%d 次"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 导出功能
        csv = df[display_columns].to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 导出成本明细",
            csv,
            f"模具成本明细_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info("暂无成本数据")

def show_downtime_analysis(start_date, end_date):
    """停机分析"""
    st.subheader("⏱️ 停机损失分析")
    
    # 获取停机数据
    downtime_data = get_downtime_analysis(start_date, end_date)
    
    if downtime_data:
        # 停机统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总停机时长", f"{downtime_data['total_hours']:.1f} 小时")
        
        with col2:
            st.metric("停机次数", f"{downtime_data['count']} 次")
        
        with col3:
            st.metric("平均停机时长", f"{downtime_data['avg_hours']:.1f} 小时/次")
        
        with col4:
            st.metric("停机损失率", f"{downtime_data['loss_rate']:.1f}%")
        
        st.markdown("---")
        
        # 停机原因分析
        col1, col2 = st.columns(2)
        
        with col1:
            # 停机原因分布
            reasons_df = pd.DataFrame(downtime_data['reasons'])
            
            fig = px.pie(
                reasons_df,
                values='hours',
                names='reason',
                title='停机原因分布',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 停机时间分布
            st.markdown("**停机时间TOP 5**")
            
            top_downtimes = downtime_data['top_downtimes'][:5]
            
            for idx, dt in enumerate(top_downtimes, 1):
                st.markdown(f"""
                **{idx}. {dt['mold_name']}**
                - 停机时长: {dt['hours']:.1f} 小时
                - 损失金额: ¥{dt['cost']:,.2f}
                - 停机原因: {dt['reason']}
                - 发生时间: {dt['date']}
                """)
                
                if idx < len(top_downtimes):
                    st.markdown("---")
        
        # 停机趋势图
        st.markdown("### 📊 停机趋势分析")
        
        trend_df = pd.DataFrame(downtime_data['trend'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=trend_df['date'],
            y=trend_df['hours'],
            name='停机时长',
            yaxis='y',
            marker_color='#FF6B6B'
        ))
        
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['cost'],
            mode='lines+markers',
            name='停机损失',
            yaxis='y2',
            line=dict(color='#4ECDC4', width=3)
        ))
        
        fig.update_layout(
            title='停机时长与损失趋势',
            xaxis_title='日期',
            yaxis=dict(
                title='停机时长 (小时)',
                side='left'
            ),
            yaxis2=dict(
                title='停机损失 (元)',
                side='right',
                overlaying='y'
            ),
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 预防建议
        st.markdown("### 💡 减少停机的建议")
        
        suggestions = generate_downtime_reduction_suggestions(downtime_data)
        
        for suggestion in suggestions:
            st.info(f"• {suggestion}")
    else:
        st.info("暂无停机数据")

def show_cost_optimization_suggestions():
    """成本优化建议"""
    st.subheader("💡 成本优化建议")
    
    # 获取优化建议数据
    optimization_data = get_optimization_suggestions()
    
    if optimization_data:
        # 潜在节省金额
        potential_savings = optimization_data['potential_savings']
        
        st.markdown(
            f"<div class='saving-metric'>潜在年度节省: ¥{potential_savings:,.2f}</div>",
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        # 优化建议列表
        for idx, suggestion in enumerate(optimization_data['suggestions'], 1):
            with st.expander(f"{suggestion['priority_icon']} {suggestion['title']}", 
                           expanded=(idx <= 3)):
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**问题描述**: {suggestion['problem']}")
                    st.markdown(f"**建议措施**: {suggestion['solution']}")
                    st.markdown(f"**预期效果**: {suggestion['expected_result']}")
                
                with col2:
                    st.metric(
                        "预计节省",
                        f"¥{suggestion['saving']:,.0f}",
                        delta=f"{suggestion['roi']:.0f}% ROI"
                    )
                
                # 实施步骤
                if suggestion.get('steps'):
                    st.markdown("**实施步骤**:")
                    for step in suggestion['steps']:
                        st.markdown(f"- {step}")
                
                # 相关模具
                if suggestion.get('related_molds'):
                    st.markdown("**相关模具**:")
                    molds_str = ", ".join(suggestion['related_molds'][:5])
                    if len(suggestion['related_molds']) > 5:
                        molds_str += f" 等{len(suggestion['related_molds'])}个"
                    st.markdown(molds_str)
        
        # 成本控制目标设定
        st.markdown("### 🎯 成本控制目标")
        
        col1, col2 = st.columns(2)
        
        with col1:
            maintenance_target = st.number_input(
                "月度维修成本目标 (元)",
                min_value=0,
                value=optimization_data.get('current_maintenance_cost', 100000),
                step=1000
            )
            
            downtime_target = st.number_input(
                "月度停机损失目标 (元)",
                min_value=0,
                value=optimization_data.get('current_downtime_cost', 50000),
                step=1000
            )
        
        with col2:
            if st.button("设定目标", type="primary"):
                save_cost_targets(maintenance_target, downtime_target)
                st.success("✅ 成本控制目标已设定！")
                st.balloons()
    else:
        st.info("正在生成优化建议...")

# 辅助函数
def get_date_range(time_range):
    """获取时间范围"""
    today = datetime.now().date()
    
    if time_range == "本月":
        start_date = today.replace(day=1)
        end_date = today
    elif time_range == "上月":
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif time_range == "本季度":
        quarter = (today.month - 1) // 3
        start_date = today.replace(month=quarter * 3 + 1, day=1)
        end_date = today
    elif time_range == "本年":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    return start_date, end_date

def get_cost_summary(start_date, end_date):
    """获取成本汇总数据"""
    # 实际实现需要从数据库查询
    # 这里返回示例数据
    return {
        'total_cost': 158000.00,
        'maintenance_cost': 68000.00,
        'downtime_cost': 45000.00,
        'avg_cost_per_mold': 3200.00,
        'cost_change': -12.5,
        'maintenance_change': -8.3,
        'downtime_change': -15.2,
        'avg_change': -10.1
    }

def get_cost_trend_data(start_date, end_date):
    """获取成本趋势数据"""
    query = """
    SELECT 
        DATE_TRUNC('day', cost_date) as date,
        SUM(CASE WHEN cost_type = '维修成本' THEN amount ELSE 0 END) as maintenance_cost,
        SUM(CASE WHEN cost_type = '停机损失' THEN amount ELSE 0 END) as downtime_cost,
        SUM(amount) as total_cost
    FROM cost_records
    WHERE cost_date BETWEEN %s AND %s
    GROUP BY DATE_TRUNC('day', cost_date)
    ORDER BY date
    """
    
    try:
        results = execute_query(query, params=(start_date, end_date), fetch_all=True)
        return [dict(r) for r in results] if results else []
    except Exception as e:
        st.error(f"获取趋势数据失败: {e}")
        return []

def get_cost_composition(start_date, end_date):
    """获取成本构成"""
    query = """
    SELECT 
        cost_type,
        SUM(amount) as total_amount
    FROM cost_records
    WHERE cost_date BETWEEN %s AND %s
    GROUP BY cost_type
    """
    
    try:
        results = execute_query(query, params=(start_date, end_date), fetch_all=True)
        
        if results:
            total = sum(r['total_amount'] for r in results)
            
            return {
                'names': [r['cost_type'] for r in results],
                'values': [r['total_amount'] for r in results],
                'changes': [
                    {
                        'name': r['cost_type'],
                        'percentage': (r['total_amount'] / total * 100) if total > 0 else 0,
                        'change': -5.2  # 示例数据，实际需要计算
                    }
                    for r in results
                ]
            }
        return {'names': [], 'values': [], 'changes': []}
    except Exception as e:
        st.error(f"获取成本构成失败: {e}")
        return {'names': [], 'values': [], 'changes': []}

def get_mold_cost_details(start_date, end_date, cost_type_filter, sort_by, top_n):
    """获取模具成本明细"""
    # 实际实现需要复杂的SQL查询
    # 返回示例数据
    sample_data = []
    for i in range(top_n):
        sample_data.append({
            'mold_code': f'LM{str(i+1).zfill(3)}',
            'mold_name': f'Φ{30+i*5}钛平底杯-落料模',
            'maintenance_cost': 5000 + i * 1000,
            'downtime_cost': 3000 + i * 500,
            'total_cost': 8000 + i * 1500,
            'maintenance_count': 3 + i % 3,
            'cost_per_use': (8000 + i * 1500) / (1000 + i * 100),
            'cost_percentage': (8000 + i * 1500) / 158000 * 100
        })
    
    return sample_data

def get_downtime_analysis(start_date, end_date):
    """获取停机分析数据"""
    # 返回示例数据
    return {
        'total_hours': 156.5,
        'count': 23,
        'avg_hours': 6.8,
        'loss_rate': 3.2,
        'reasons': [
            {'reason': '模具故障', 'hours': 65.5, 'percentage': 41.9},
            {'reason': '计划保养', 'hours': 38.0, 'percentage': 24.3},
            {'reason': '更换部件', 'hours': 28.0, 'percentage': 17.9},
            {'reason': '其他原因', 'hours': 25.0, 'percentage': 16.0}
        ],
        'top_downtimes': [
            {
                'mold_name': 'LM001-Φ50钛平底杯',
                'hours': 18.5,
                'cost': 12500,
                'reason': '压边圈严重磨损',
                'date': '2024-05-15'
            },
            {
                'mold_name': 'YS201-Φ50钛平底杯-二引模',
                'hours': 15.0,
                'cost': 10000,
                'reason': '模具精度调整',
                'date': '2024-05-20'
            }
        ],
        'trend': [
            {'date': '2024-05-01', 'hours': 8.5, 'cost': 5500},
            {'date': '2024-05-08', 'hours': 12.0, 'cost': 8000},
            {'date': '2024-05-15', 'hours': 18.5, 'cost': 12500},
            {'date': '2024-05-22', 'hours': 6.0, 'cost': 4000}
        ]
    }

def generate_downtime_reduction_suggestions(downtime_data):
    """生成减少停机的建议"""
    suggestions = []
    
    # 基于数据生成建议
    if downtime_data['avg_hours'] > 5:
        suggestions.append("建立快速维修响应机制，配备常用备件库存，减少等待时间")
    
    # 检查主要原因
    top_reason = downtime_data['reasons'][0]
    if top_reason['reason'] == '模具故障' and top_reason['percentage'] > 40:
        suggestions.append("加强预防性维护，建立模具健康监测系统，提前发现潜在问题")
    
    if downtime_data['loss_rate'] > 3:
        suggestions.append("优化生产排程，将维护保养安排在非生产高峰期")
    
    suggestions.append("建立模具备用机制，关键模具准备备用件")
    suggestions.append("加强操作工培训，减少因操作不当导致的模具损坏")
    
    return suggestions

def get_optimization_suggestions():
    """获取成本优化建议"""
    # 实际实现需要基于数据分析
    return {
        'potential_savings': 235000,
        'current_maintenance_cost': 120000,
        'current_downtime_cost': 80000,
        'suggestions': [
            {
                'priority_icon': '🔴',
                'title': '优化高成本模具维修策略',
                'problem': '5个模具占总维修成本的45%，维修频率异常高',
                'solution': '对这5个模具进行全面检修或考虑更换，建立专门维护计划',
                'expected_result': '预计降低30%的维修频率',
                'saving': 45000,
                'roi': 150,
                'steps': [
                    '识别高成本模具清单',
                    '分析故障根本原因',
                    '制定专项改善计划',
                    '实施并跟踪效果'
                ],
                'related_molds': ['LM001', 'LM002', 'YS201', 'YS202', 'QM001']
            },
            {
                'priority_icon': '🟡',
                'title': '建立预测性维护体系',
                'problem': '目前主要是事后维修，导致突发停机多',
                'solution': '基于使用数据建立维护预测模型，提前安排保养',
                'expected_result': '减少60%的突发停机',
                'saving': 35000,
                'roi': 200,
                'steps': [
                    '收集历史维修数据',
                    '建立预测模型',
                    '制定预防性维护计划',
                    '培训维护人员'
                ]
            },
            {
                'priority_icon': '🟢',
                'title': '优化备件管理',
                'problem': '关键备件缺货导致维修等待时间长',
                'solution': '建立智能备件库存管理系统',
                'expected_result': '减少50%的等待时间',
                'saving': 25000,
                'roi': 120,
                'steps': [
                    '分析备件使用频率',
                    '设定安全库存',
                    '建立补货机制'
                ]
            }
        ]
    }

def save_cost_targets(maintenance_target, downtime_target):
    """保存成本目标"""
    # 实际实现需要保存到数据库
    from utils.auth import log_user_action
    log_user_action('SET_COST_TARGET', 'cost_management', 
                   f"maintenance:{maintenance_target},downtime:{downtime_target}")

if __name__ == "__main__":
    # 模拟登录状态用于测试
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = 1
        st.session_state['user_role'] = '模具库管理员'
        st.session_state['username'] = 'test_admin'
    
    show()