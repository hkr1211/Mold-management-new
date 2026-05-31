# pages/7_模具推荐.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import execute_query
from utils.auth import require_permission
from utils.ui import inject_global_css, page_header
from utils.nav import setup_sidebar


def _build_recommendation_history_query():
    """构建兼容当前 SQLite schema 的推荐历史查询"""
    return """
    SELECT
        mr.recommendation_id,
        mr.created_at,
        '' AS order_code,
        COALESCE(p.product_name, '') AS product_name,
        m.mold_code,
        m.mold_name,
        mr.score AS recommendation_score,
        0 AS is_selected,
        mr.reason AS recommendation_reason
    FROM mold_recommendations mr
    LEFT JOIN products p ON mr.product_id = p.product_id
    LEFT JOIN molds m ON mr.mold_id = m.mold_id
    WHERE mr.created_at BETWEEN %s AND %s
    ORDER BY mr.created_at DESC
    """


def _build_save_recommendation_insert_query():
    """构建兼容当前 SQLite schema 的推荐结果保存 SQL"""
    return """
    INSERT INTO mold_recommendations
    (mold_id, product_id, score, reason, created_at)
    VALUES (%s, %s, %s, %s, %s)
    """

@require_permission('view_molds')
def show():
    """模具推荐主页面"""
    inject_global_css()
    setup_sidebar("6_模具推荐.py")
    page_header("🤖", "智能模具推荐", "综合评分 · 智能匹配 · 推荐历史")
    
    # 添加使用说明
    with st.expander("💡 使用说明", expanded=False):
        st.markdown("""
        ### 功能说明
        - 根据产品规格自动推荐最合适的模具
        - 综合考虑模具状态、剩余寿命、位置等因素
        - 提供详细的推荐理由和评分
        
        ### 推荐因素
        1. **模具匹配度**：产品规格与模具的匹配程度
        2. **可用性**：模具当前是否可用
        3. **剩余寿命**：优先推荐寿命充足的模具
        4. **位置便利性**：就近原则，减少搬运时间
        5. **维护状态**：刚保养过的模具优先级更高
        """)
    
    # 主要功能区
    tab1, tab2, tab3 = st.tabs(["📋 订单模具推荐", "🔍 快速查询", "📊 推荐历史"])
    
    with tab1:
        show_order_recommendation()
    
    with tab2:
        show_quick_search()
    
    with tab3:
        show_recommendation_history()

def show_order_recommendation():
    """订单模具推荐"""
    st.subheader("📋 根据订单推荐模具")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 输入订单信息
        order_code = st.text_input("订单编号", placeholder="例如: PO-2024-001")
        
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_order = st.button("🔍 查询订单", type="primary")
    
    if order_code and search_order:
        # 查询订单信息
        order_info = get_order_info(order_code)
        
        if order_info:
            # 显示订单信息
            st.info(f"""
            **订单信息**
            - 产品: {order_info['product_name']} ({order_info['product_code']})
            - 数量: {order_info['quantity']:,} 件
            - 交期: {order_info['due_date']}
            - 优先级: {'⭐' * order_info['priority']}
            """)
            
            # 获取推荐模具
            recommendations = get_mold_recommendations(order_info)
            
            if recommendations:
                st.success(f"找到 {len(recommendations)} 个可用模具")
                
                # 显示推荐结果
                for idx, rec in enumerate(recommendations):
                    show_recommendation_card(rec, idx + 1)
                    
                    # 选择按钮
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col2:
                        if st.button(f"选择此模具", key=f"select_{rec['mold_id']}"):
                            save_recommendation_selection(order_code, rec['mold_id'])
                            st.success("✅ 已选择模具！")
                            st.balloons()
            else:
                st.warning("没有找到合适的模具")
        else:
            st.error("未找到订单信息")
    
    # 手动输入产品信息
    with st.expander("手动输入产品信息", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            product_type = st.selectbox("产品类型", ["平底圆杯", "异形杯", "金属圆片"])
            product_spec = st.text_input("产品规格", placeholder="例如: Φ50")
            material = st.selectbox("材料", ["钛", "钼", "锆", "铌", "钽", "钴", "铜", "铁"])
        
        with col2:
            quantity = st.number_input("生产数量", min_value=1, value=1000)
            priority = st.slider("优先级", 1, 10, 5)
            
        if st.button("获取推荐", type="primary"):
            # 构造虚拟订单信息
            virtual_order = {
                'product_type': product_type,
                'product_spec': product_spec,
                'material': material,
                'quantity': quantity,
                'priority': priority
            }
            
            recommendations = get_mold_recommendations_by_spec(virtual_order)
            
            if recommendations:
                st.success(f"找到 {len(recommendations)} 个可用模具")
                for idx, rec in enumerate(recommendations):
                    show_recommendation_card(rec, idx + 1)
            else:
                st.warning("没有找到合适的模具")

def show_recommendation_card(rec, rank):
    """显示推荐卡片"""
    # 计算推荐等级
    score = rec['score']
    if score >= 90:
        level = "🥇 最佳选择"
        color = "#4CAF50"
    elif score >= 80:
        level = "🥈 推荐使用"
        color = "#2196F3"
    elif score >= 70:
        level = "🥉 可以使用"
        color = "#FF9800"
    else:
        level = "⚠️ 备选方案"
        color = "#757575"
    
    with st.expander(f"#{rank} {rec['mold_code']} - {rec['mold_name']} ({level})", expanded=(rank == 1)):
        # 推荐评分可视化
        fig = create_score_radar(rec)
        st.plotly_chart(fig, use_container_width=True)
        
        # 详细信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**基本信息**")
            st.write(f"- 模具编号: {rec['mold_code']}")
            st.write(f"- 模具类型: {rec['mold_type']}")
            st.write(f"- 当前状态: {rec['status']}")
            st.write(f"- 存放位置: {rec['location']}")
            
        with col2:
            st.markdown("**使用情况**")
            st.write(f"- 总寿命: {rec['total_life']:,} 冲次")
            st.write(f"- 已使用: {rec['used_life']:,} 冲次")
            st.write(f"- 剩余寿命: {rec['remaining_life']:,} 冲次")
            
            # 寿命进度条
            life_percent = (rec['used_life'] / rec['total_life']) * 100 if rec['total_life'] > 0 else 0
            st.progress(min(life_percent / 100, 1.0))
            st.caption(f"寿命使用率: {life_percent:.1f}%")
        
        # 推荐理由
        st.markdown("**推荐理由**")
        for reason in rec['reasons']:
            st.write(f"- {reason}")
        
        # 风险提示
        if rec.get('risks'):
            st.warning("**注意事项**")
            for risk in rec['risks']:
                st.write(f"⚠️ {risk}")

def create_score_radar(rec):
    """创建评分雷达图"""
    categories = ['匹配度', '可用性', '剩余寿命', '位置便利', '维护状态']
    values = [
        rec['match_score'],
        rec['availability_score'],
        rec['life_score'],
        rec['location_score'],
        rec['maintenance_score']
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='综合评分'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title=f"综合评分: {rec['score']:.1f}分",
        height=300
    )
    
    return fig

def get_mold_recommendations(order_info):
    """获取模具推荐列表"""
    # 这里应该实现复杂的推荐算法
    # 简化示例
    query = """
    WITH mold_scores AS (
        SELECT 
            m.mold_id,
            m.mold_code,
            m.mold_name,
            mft.type_name as mold_type,
            ms.status_name as status,
            sl.location_name as location,
            m.theoretical_lifespan_strokes as total_life,
            m.accumulated_strokes as used_life,
            m.theoretical_lifespan_strokes - m.accumulated_strokes as remaining_life,
            -- 计算各项评分
            CASE 
                WHEN ms.status_name = '闲置' THEN 100
                WHEN ms.status_name IN ('已预定', '外借申请中') THEN 50
                ELSE 0
            END as availability_score,
            CASE 
                WHEN m.theoretical_lifespan_strokes > 0 
                THEN LEAST(100, (m.theoretical_lifespan_strokes - m.accumulated_strokes) * 100.0 / m.theoretical_lifespan_strokes)
                ELSE 80
            END as life_score,
            80 as match_score, -- 简化处理
            90 as location_score, -- 简化处理
            85 as maintenance_score -- 简化处理
        FROM molds m
        JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        JOIN mold_statuses ms ON m.current_status_id = ms.status_id
        LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
        WHERE ms.status_name NOT IN ('报废', '维修中')
    )
    SELECT 
        *,
        (availability_score * 0.3 + life_score * 0.25 + match_score * 0.25 + 
         location_score * 0.1 + maintenance_score * 0.1) as score
    FROM mold_scores
    WHERE availability_score > 0
    ORDER BY score DESC
    LIMIT 5
    """
    
    try:
        results = execute_query(query, fetch_all=True)
        
        # 添加推荐理由
        recommendations = []
        for row in results:
            rec = dict(row)
            rec['reasons'] = generate_recommendation_reasons(rec)
            rec['risks'] = generate_risk_warnings(rec)
            recommendations.append(rec)
        
        return recommendations
    except Exception as e:
        st.error(f"获取推荐失败: {e}")
        return []

def generate_recommendation_reasons(mold):
    """生成推荐理由"""
    reasons = []
    
    if mold['availability_score'] == 100:
        reasons.append("✅ 模具当前处于闲置状态，立即可用")
    
    if mold['life_score'] >= 80:
        reasons.append(f"✅ 剩余寿命充足 ({mold['remaining_life']:,} 冲次)")
    
    if mold['match_score'] >= 90:
        reasons.append("✅ 模具规格与产品完全匹配")
    
    if mold['location_score'] >= 85:
        reasons.append("✅ 存放位置便于取用")
    
    if mold['maintenance_score'] >= 85:
        reasons.append("✅ 模具维护状态良好")
    
    return reasons

def generate_risk_warnings(mold):
    """生成风险提示"""
    risks = []
    
    life_percent = (mold['used_life'] / mold['total_life'] * 100) if mold['total_life'] > 0 else 0
    
    if life_percent > 80:
        risks.append(f"模具寿命已使用 {life_percent:.1f}%，建议准备备用模具")
    
    if mold['availability_score'] < 100:
        risks.append("模具可能需要等待或协调")
    
    # 这里可以添加更多风险判断逻辑
    
    return risks

def show_quick_search():
    """快速查询模具"""
    st.subheader("🔍 快速查询模具状态")
    
    # 搜索框
    search_term = st.text_input("输入模具编号或名称", placeholder="例如: LM001")
    
    if search_term:
        # 查询模具信息
        query = """
        SELECT 
            m.mold_id,
            m.mold_code,
            m.mold_name,
            mft.type_name as mold_type,
            ms.status_name as status,
            sl.location_name as location,
            m.theoretical_lifespan_strokes,
            m.accumulated_strokes,
            m.maintenance_cycle_strokes,
            CASE 
                WHEN m.theoretical_lifespan_strokes > 0 
                THEN ROUND((m.accumulated_strokes::DECIMAL / m.theoretical_lifespan_strokes) * 100, 2)
                ELSE 0
            END as usage_percentage
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
        LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
        WHERE m.mold_code ILIKE %s OR m.mold_name ILIKE %s
        """
        
        try:
            search_pattern = f"%{search_term}%"
            results = execute_query(query, params=(search_pattern, search_pattern), fetch_all=True)
            
            if results:
                for mold in results:
                    with st.expander(f"{mold['mold_code']} - {mold['mold_name']}", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("当前状态", mold['status'])
                            st.metric("存放位置", mold['location'])
                        
                        with col2:
                            st.metric("使用率", f"{mold['usage_percentage']}%")
                            remaining = mold['theoretical_lifespan_strokes'] - mold['accumulated_strokes']
                            st.metric("剩余寿命", f"{remaining:,} 冲次")
                        
                        with col3:
                            if mold['status'] == '闲置':
                                st.success("✅ 可立即使用")
                            elif mold['status'] in ['已借出', '使用中']:
                                st.warning("⚠️ 使用中")
                            else:
                                st.error("❌ 不可用")
                            
                            if st.button(f"查看详情", key=f"detail_{mold['mold_id']}"):
                                st.session_state['selected_mold_id'] = mold['mold_id']
            else:
                st.info("未找到匹配的模具")
                
        except Exception as e:
            st.error(f"查询失败: {e}")

def show_recommendation_history():
    """推荐历史记录"""
    st.subheader("📊 模具推荐历史")
    
    # 时间范围选择
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("结束日期", datetime.now())
    
    # 查询推荐历史
    query = _build_recommendation_history_query()
    
    try:
        results = execute_query(query, params=(start_date, end_date), fetch_all=True)
        
        if results:
            # 统计信息
            total_recommendations = len(results)
            selected_count = len([r for r in results if r.get('is_selected')])
            acceptance_rate = (selected_count / total_recommendations * 100) if total_recommendations > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总推荐次数", total_recommendations)
            with col2:
                st.metric("采纳次数", selected_count)
            with col3:
                st.metric("采纳率", f"{acceptance_rate:.1f}%")
            
            # 显示历史记录
            st.markdown("---")
            
            df = pd.DataFrame(results)
            df['推荐时间'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            df['是否采纳'] = df['is_selected'].map({True: '✅ 已采纳', False: '❌ 未采纳', 0: '❌ 未采纳'})
            df['推荐分数'] = df['recommendation_score'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(
                df[['推荐时间', 'order_code', 'product_name', 'mold_code', 'mold_name', '推荐分数', '是否采纳']],
                column_config={
                    'order_code': '订单编号',
                    'product_name': '产品名称',
                    'mold_code': '模具编号',
                    'mold_name': '模具名称'
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("暂无推荐历史记录")
            
    except Exception as e:
        st.error(f"查询失败: {e}")

# 辅助函数
def get_order_info(order_code):
    """获取订单信息"""
    query = """
    SELECT 
        po.order_id,
        po.order_code,
        po.quantity,
        po.due_date,
        po.priority,
        p.product_id,
        p.product_code,
        p.product_name,
        pt.type_name as product_type,
        m.material_name
    FROM production_orders po
    JOIN products p ON po.product_id = p.product_id
    JOIN product_types pt ON p.product_type_id = pt.type_id
    JOIN materials m ON p.material_id = m.material_id
    WHERE po.order_code = %s
    """
    
    try:
        result = execute_query(query, params=(order_code,), fetch_one=True)
        return dict(result) if result else None
    except Exception as e:
        st.error(f"查询订单失败: {e}")
        return None

def get_mold_recommendations_by_spec(spec_info):
    """根据产品规格获取推荐"""
    # 这里可以实现更复杂的匹配算法
    return get_mold_recommendations(spec_info)

def save_recommendation_selection(order_code, mold_id):
    """保存推荐选择"""
    try:
        order_query = """
        SELECT order_id, product_id
        FROM production_orders
        WHERE order_code = %s
        """
        order_result = execute_query(order_query, params=(order_code,), fetch_one=True)

        if order_result:
            insert_query = _build_save_recommendation_insert_query()
            execute_query(
                insert_query,
                params=(
                    mold_id,
                    order_result['product_id'],
                    100.0,
                    f"订单 {order_code} 选择了该模具",
                    datetime.now()
                ),
                commit=True
            )

            from utils.auth import log_user_action
            log_user_action('SELECT_MOLD', 'mold_recommendations', f"{order_code}_{mold_id}")
            
    except Exception as e:
        st.error(f"保存选择失败: {e}")

show()
