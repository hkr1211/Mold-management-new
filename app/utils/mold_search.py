# utils/mold_search.py - 可选的搜索组件增强
import streamlit as st
import pandas as pd
from utils.database import execute_query

def create_mold_search_widget():
    """创建模具搜索组件"""
    
    # 搜索配置
    search_config = {
        'placeholder': '🔍 搜索模具 (编号/名称/类型)',
        'help': '支持模糊搜索，例如: LM001, 钛杯, 落料模',
        'max_results': 20,
        'min_search_length': 2
    }
    
    # 搜索输入
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_query = st.text_input(
            "搜索模具",
            placeholder=search_config['placeholder'],
            help=search_config['help'],
            key="mold_search_input"
        )
    
    with col2:
        search_type = st.selectbox(
            "搜索范围",
            options=["仅可用", "全部模具"],
            key="search_scope"
        )
    
    with col3:
        # 实时搜索开关
        real_time_search = st.checkbox(
            "实时搜索", 
            value=True,
            help="输入时自动搜索"
        )
    
    # 搜索逻辑
    results = []
    show_results = False
    
    if search_query and len(search_query) >= search_config['min_search_length']:
        if real_time_search or st.button("🔍 搜索", key="manual_search"):
            show_results = True
            results = perform_mold_search(
                search_query, 
                only_available=(search_type == "仅可用"),
                max_results=search_config['max_results']
            )
    
    return search_query, results, show_results

def perform_mold_search(query, only_available=True, max_results=20):
    """执行模具搜索"""
    try:
        # 构建基础查询
        base_sql = """
        SELECT 
            m.mold_id,
            m.mold_code,
            m.mold_name,
            mft.type_name as functional_type,
            ms.status_name as current_status,
            sl.location_name as current_location,
            COALESCE(m.theoretical_lifespan_strokes, 0) as theoretical_lifespan,
            COALESCE(m.accumulated_strokes, 0) as accumulated_strokes
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
        LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
        WHERE (
            m.mold_code ILIKE %s OR 
            m.mold_name ILIKE %s OR 
            mft.type_name ILIKE %s
        )
        """
        
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
        
        # 如果只搜索可用模具
        if only_available:
            base_sql += " AND ms.status_name = '闲置'"
        
        base_sql += f" ORDER BY m.mold_code LIMIT {max_results}"
        
        results = execute_query(base_sql, params, fetch_all=True)
        return results if results else []
        
    except Exception as e:
        st.error(f"搜索失败: {e}")
        return []

def display_mold_search_results(results, selectable=True, show_details=True):
    """显示搜索结果"""
    if not results:
        st.info("未找到匹配的模具")
        return None
    
    st.success(f"找到 {len(results)} 个匹配结果")
    
    selected_mold = None
    
    for i, mold in enumerate(results):
        # 状态图标
        status_icons = {
            "闲置": "🟢",
            "使用中": "🟡", 
            "已借出": "🟠",
            "维修中": "🔴",
            "保养中": "🟣"
        }
        
        status_icon = status_icons.get(mold.get('current_status', ''), "⚪")
        
        # 使用率计算
        theoretical = mold.get('theoretical_lifespan', 0)
        accumulated = mold.get('accumulated_strokes', 0)
        usage_rate = (accumulated / theoretical * 100) if theoretical > 0 else 0
        
        # 创建展示框
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{status_icon} {mold['mold_code']}** - {mold['mold_name']}")
                st.caption(f"类型: {mold.get('functional_type', '未知')} | 位置: {mold.get('current_location', '未知')}")
            
            with col2:
                if show_details:
                    if theoretical > 0:
                        st.metric(
                            "使用率", 
                            f"{usage_rate:.1f}%",
                            delta=f"{accumulated:,}/{theoretical:,}"
                        )
                    else:
                        st.metric("状态", mold.get('current_status', '未知'))
            
            with col3:
                if selectable and mold.get('current_status') == '闲置':
                    if st.button(
                        "✅ 选择", 
                        key=f"select_{mold['mold_id']}", 
                        type="primary",
                        use_container_width=True
                    ):
                        selected_mold = mold
                elif selectable:
                    st.button(
                        "❌ 不可用", 
                        key=f"unavail_{mold['mold_id']}", 
                        disabled=True,
                        use_container_width=True
                    )
        
        st.divider()
    
    return selected_mold

def create_quick_mold_selector():
    """创建快速模具选择器"""
    st.markdown("### 🔍 快速选择模具")
    
    # 热门/最近使用的模具
    with st.expander("⭐ 常用模具", expanded=True):
        popular_molds = get_popular_molds()
        if popular_molds:
            cols = st.columns(min(len(popular_molds), 4))
            for i, mold in enumerate(popular_molds[:4]):
                with cols[i]:
                    if st.button(
                        f"🔧 {mold['mold_code']}",
                        key=f"popular_{mold['mold_id']}",
                        help=f"{mold['mold_name']} - {mold.get('functional_type', '未知类型')}",
                        use_container_width=True
                    ):
                        return mold
    
    # 按类型快速筛选
    with st.expander("📂 按类型筛选", expanded=False):
        mold_types = get_mold_types()
        if mold_types:
            selected_type = st.selectbox(
                "选择模具类型",
                options=["全部"] + [t['type_name'] for t in mold_types],
                key="type_filter"
            )
            
            if selected_type != "全部":
                type_molds = get_molds_by_type(selected_type)
                if type_molds:
                    selected = st.selectbox(
                        f"选择{selected_type}",
                        options=type_molds,
                        format_func=lambda x: f"{x['mold_code']} - {x['mold_name']}",
                        key="type_mold_selector"
                    )
                    if st.button("确认选择", key="confirm_type_selection"):
                        return selected
    
    return None

def get_popular_molds(limit=8):
    """获取热门模具（基于使用频率）"""
    query = """
    SELECT 
        m.mold_id, m.mold_code, m.mold_name,
        mft.type_name as functional_type,
        COUNT(mlr.loan_id) as usage_count
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    LEFT JOIN mold_loan_records mlr ON m.mold_id = mlr.mold_id
    WHERE ms.status_name = '闲置'
    GROUP BY m.mold_id, m.mold_code, m.mold_name, mft.type_name
    ORDER BY usage_count DESC, m.mold_code
    LIMIT %s
    """
    
    try:
        return execute_query(query, (limit,), fetch_all=True) or []
    except:
        return []

def get_mold_types():
    """获取模具类型列表"""
    query = "SELECT type_id, type_name FROM mold_functional_types ORDER BY type_name"
    try:
        return execute_query(query, fetch_all=True) or []
    except:
        return []

def get_molds_by_type(type_name, limit=10):
    """根据类型获取可用模具"""
    query = """
    SELECT m.mold_id, m.mold_code, m.mold_name
    FROM molds m
    JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    WHERE mft.type_name = %s AND ms.status_name = '闲置'
    ORDER BY m.mold_code
    LIMIT %s
    """
    
    try:
        return execute_query(query, (type_name, limit), fetch_all=True) or []
    except:
        return []