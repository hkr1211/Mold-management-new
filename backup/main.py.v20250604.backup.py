# main.py
import streamlit as st
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 设置页面配置
st.set_page_config(
    page_title="蕴杰金属冲压模具管理系统",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入页面模块
try:
    from pages import , loan_management
    from utils.database import test_connection
except ImportError as e:
    st.error(f"模块导入失败: {e}")
    st.stop()

def check_authentication():
    """检查用户认证状态"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def show_login():
    """显示登录页面"""
    st.title("🔧 蕴杰金属冲压模具管理系统")
    st.markdown("---")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("🔐 系统登录")
            
            with st.form("login_form"):
                username = st.text_input("用户名", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", placeholder="请输入密码")
                
                submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
                
                if submitted:
                    # 简单的演示登录逻辑（实际项目中应该验证数据库）
                    if username and password:
                        if username == "admin" and password == "admin123":
                            st.session_state.authenticated = True
                            st.session_state.user_id = 1
                            st.session_state.username = username
                            st.session_state.user_role = "超级管理员"
                            st.success("登录成功！")
                            st.rerun()
                        elif username == "mold_admin" and password == "mold123":
                            st.session_state.authenticated = True
                            st.session_state.user_id = 2
                            st.session_state.username = username
                            st.session_state.user_role = "模具库管理员"
                            st.success("登录成功！")
                            st.rerun()
                        elif username == "technician" and password == "tech123":
                            st.session_state.authenticated = True
                            st.session_state.user_id = 3
                            st.session_state.username = username
                            st.session_state.user_role = "模具工"
                            st.success("登录成功！")
                            st.rerun()
                        elif username == "operator" and password == "op123":
                            st.session_state.authenticated = True
                            st.session_state.user_id = 4
                            st.session_state.username = username
                            st.session_state.user_role = "冲压操作工"
                            st.success("登录成功！")
                            st.rerun()
                        else:
                            st.error("用户名或密码错误！")
                    else:
                        st.error("请输入用户名和密码！")
            
            # 演示账号说明
            st.markdown("---")
            st.markdown("**演示账号：**")
            st.markdown("""
            - 超级管理员：admin / admin123
            - 模具库管理员：mold_admin / mold123  
            - 模具工：technician / tech123
            - 冲压操作工：operator / op123
            """)

def show_navigation():
    """显示导航菜单"""
    with st.sidebar:
        st.title("🔧 模具管理系统")
        st.markdown(f"**欢迎，{st.session_state.get('username', '用户')}**")
        st.markdown(f"**角色：{st.session_state.get('user_role', '未知')}**")
        st.markdown("---")
        
        # 根据用户角色显示不同的菜单
        user_role = st.session_state.get('user_role', '')
        
        # 通用菜单
        menu_options = []
        
        if user_role in ["超级管理员", "模具库管理员"]:
            menu_options.extend([
                "📋 模具管理",
                "🔧 部件管理", 
                "📦 产品管理",
                "📤 借用管理",
                "🔄 使用记录"
            ])
        
        if user_role in ["超级管理员", "模具库管理员", "模具工"]:
            menu_options.append("🛠️ 维修保养")
        
        if user_role == "冲压操作工":
            menu_options.extend([
                "🔍 模具查询",
                "📝 借用管理",
                "📊 我的记录"
            ])
        
        if user_role == "超级管理员":
            menu_options.extend([
                "👥 用户管理",
                "⚙️ 系统设置"
            ])
        
        menu_options.append("📈 统计报表")
        
        # 菜单选择 - 使用session_state保持状态
        if 'selected_menu' not in st.session_state:
            st.session_state.selected_menu = "请选择..."
        
        selected = st.selectbox(
            "选择功能", 
            ["请选择..."] + menu_options,
            index=0 if st.session_state.selected_menu == "请选择..." else (
                menu_options.index(st.session_state.selected_menu) + 1 
                if st.session_state.selected_menu in menu_options else 0
            ),
            key="menu_selector"
        )
        
        # 更新session state
        if selected != "请选择...":
            st.session_state.selected_menu = selected
        
        # 登出按钮
        st.markdown("---")
        if st.button("🚪 退出登录", use_container_width=True):
            for key in ['authenticated', 'user_id', 'username', 'user_role', 'selected_menu']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        # 数据库连接状态
        st.markdown("---")
        st.markdown("**系统状态**")
        try:
            if test_connection():
                st.success("🟢 数据库连接正常")
            else:
                st.error("🔴 数据库连接异常")
        except:
            st.warning("🟡 数据库状态未知")
    
    return selected

def show_dashboard():
    """显示系统仪表板"""
    st.title("🏠 蕴杰金属冲压模具管理系统")
    st.markdown("---")
    
    # 尝试获取真实数据
    try:
        from utils.database import get_all_molds, get_mold_statuses
        
        # 获取模具数据
        all_molds = get_all_molds() or []
        statuses = get_mold_statuses() or []
        
        # 计算统计数据
        total_molds = len(all_molds)
        available_molds = len([m for m in all_molds if m.get('current_status') in ['闲置', '可用']])
        in_maintenance = len([m for m in all_molds if m.get('current_status') in ['维修中', '保养中', '待维修', '待保养']])
        borrowed = len([m for m in all_molds if m.get('current_status') in ['已借出', '使用中']])
        
    except Exception as e:
        st.warning(f"无法获取实时数据: {e}")
        total_molds = "--"
        available_molds = "--"
        in_maintenance = "--"
        borrowed = "--"
    
    # 显示系统概览
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 模具总数",
            value=total_molds,
            help="系统中管理的模具总数量"
        )
    
    with col2:
        st.metric(
            label="✅ 可用模具",
            value=available_molds,
            help="当前可用状态的模具数量"
        )
    
    with col3:
        st.metric(
            label="🔧 维护中",
            value=in_maintenance,
            help="正在维修或保养的模具数量"
        )
    
    with col4:
        st.metric(
            label="📤 已借出",
            value=borrowed,
            help="当前已借出的模具数量"
        )
    
    st.markdown("---")
    st.markdown("### 📋 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 查询模具", use_container_width=True):
            st.session_state.selected_menu = "📋 模具管理"
            st.rerun()
    
    with col2:
        if st.button("📝 借用申请", use_container_width=True):
            st.session_state.selected_menu = "📤 借用管理"
            st.rerun()
    
    with col3:
        if st.button("📊 查看报表", use_container_width=True):
            st.session_state.selected_menu = "📈 统计报表"
            st.rerun()

def main():
    """主函数"""
    # 检查认证状态
    if not check_authentication():
        show_login()
    else:
        # 显示导航菜单（始终显示）
        selected_menu = show_navigation()
        
        # 主内容区域
        with st.container():
            # 根据选择的菜单显示对应页面
            if selected_menu == "📋 模具管理":
                .show()
            elif selected_menu == "🔧 部件管理":
                st.title("🔧 部件管理")
                st.info("部件管理功能开发中...")
            elif selected_menu == "📦 产品管理":
                st.title("📦 产品管理")
                st.info("产品管理功能开发中...")
            elif selected_menu in ["📤 借用管理", "📝 借用管理"]:
                loan_management.show()
            elif selected_menu == "🔄 使用记录":
                st.title("🔄 使用记录")
                st.info("使用记录功能开发中...")
            elif selected_menu == "🛠️ 维修保养":
                st.title("🛠️ 维修保养")
                st.info("维修保养功能开发中...")
            elif selected_menu == "🔍 模具查询":
                # 为冲压操作工提供只读的模具查询界面
                from pages.mold_management import show_mold_list_readonly
                show_mold_list_readonly()
            elif selected_menu == "📊 我的记录":
                st.title("📊 我的记录")
                st.info("个人记录功能开发中...")
            elif selected_menu == "👥 用户管理":
                st.title("👥 用户管理")
                st.info("用户管理功能开发中...")
            elif selected_menu == "⚙️ 系统设置":
                st.title("⚙️ 系统设置")
                st.info("系统设置功能开发中...")
            elif selected_menu == "📈 统计报表":
                st.title("📈 统计报表")
                st.info("统计报表功能开发中...")
            else:
                # 默认首页
                show_dashboard()

if __name__ == "__main__":
    main()