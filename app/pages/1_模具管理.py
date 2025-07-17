# app/pages/1_模具管理.py (带诊断信息版)
import streamlit as st
import pandas as pd
from app.utils.database import execute_query
from app.utils.auth import has_permission

st.write("--- DEBUG: 脚本开始执行 ---") # <-- 航点 1

# --- 访问控制 ---
st.write("--- DEBUG: 即将检查登录状态... ---") # <-- 航点 2
if not st.session_state.get('logged_in', False):
    st.error("🔒 请先登录以访问此页面。")
    st.write("--- DEBUG: 登录检查失败，停止执行。 ---") # <-- 航点 2A
    st.stop()
else:
    st.write("--- DEBUG: 登录检查通过。 ---") # <-- 航点 2B

# --- 数据获取函数 ---
@st.cache_data(ttl=300)
def fetch_molds_data():
    st.write("--- DEBUG: 正在执行fetch_molds_data函数... ---") # <-- 航点 3
    query = "SELECT * FROM molds ORDER BY created_at DESC"
    try:
        data = execute_query(query, fetch_all=True)
        if data:
            st.write(f"--- DEBUG: 从数据库获取到 {len(data)} 条数据。 ---") # <-- 航点 4
            return pd.DataFrame(data)
        st.write("--- DEBUG: 数据库查询成功，但没有返回数据。 ---") # <-- 航点 5
        return pd.DataFrame()
    except Exception as e:
        st.error(f"加载模具数据失败: {e}")
        return pd.DataFrame()

# --- 主函数 ---
def mold_management_page():
    st.write("--- DEBUG: 进入 mold_management_page 函数 ---") # <-- 航点 6
    st.title("🛠️ 模具管理")
    
    molds_df = fetch_molds_data()
    
    tab1, tab2 = st.tabs(["模具列表", "新增模具"])

    with tab1:
        st.header("模具列表")
        st.write("--- DEBUG: 即将显示DataFrame... ---") # <-- 航点 7
        if molds_df.empty:
            st.warning("当前没有任何模具信息。")
        else:
            st.dataframe(molds_df, use_container_width=True)
        st.write("--- DEBUG: DataFrame显示完毕。 ---") # <-- 航点 8

    with tab2:
        st.header("新增模具")
        if has_permission('create_mold'):
            # ... 此处省略表单代码 ...
            st.write("新增模具表单（功能待实现）")
        else:
            st.warning("🔒 您的角色没有新增模具的权限。")
            
    st.write("--- DEBUG: mold_management_page 函数执行完毕 ---") # <-- 航点 9

# --- 页面执行入口 ---
st.write("--- DEBUG: 即将调用 mold_management_page 函数 ---") # <-- 航点 10
mold_management_page()
st.write("--- DEBUG: 脚本执行完毕 ---") # <-- 航点 11