# app/main.py - 完整修复版

import streamlit as st
from utils.auth import login_user, logout_user
from utils.database import execute_query, test_connection
import logging
import time
import datetime

# 配置日志，与database.py/auth.py统一
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 页面配置 ---
st.set_page_config(
    page_title="蕴杰模具管理系统",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 会话状态初始化 ---
def init_session_state():
    """初始化会话状态"""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = ''
    if 'user_role' not in st.session_state:
        st.session_state['user_role'] = ''
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'full_name' not in st.session_state:
        st.session_state['full_name'] = ''

# --- 自定义CSS样式 ---
def load_custom_css():
    """加载自定义CSS样式"""
    st.markdown("""
    <style>
        /* 隐藏Streamlit默认元素 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* 主要布局样式 */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* 登录卡片样式 */
        .login-card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin: 2rem 0;
        }
        
        /* 功能卡片样式 */
        .feature-card {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
            border-radius: 12px;
            margin-bottom: 1rem;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        /* 用户信息卡片 */
        .user-info-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        /* 输入框样式 */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #e1e5e9;
            padding: 0.75rem;
            transition: border-color 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #1f77b4;
            box-shadow: 0 0 0 0.2rem rgba(31, 119, 180, 0.25);
        }
        
        /* 按钮样式 */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            padding: 0.5rem 1rem;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* 系统标题样式 */
        .system-title {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* 度量指标样式 */
        .metric-container {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            margin-bottom: 1rem;
        }
        
        /* 活动日志样式 */
        .activity-item {
            background: white;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            border-left: 4px solid #1f77b4;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* 欢迎消息样式 */
        .welcome-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 登录界面 ---
def show_login_form():
    """显示登录表单"""
    # 页面布局
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # 系统标题和Logo
        st.markdown("""
        <div class="system-title">
            <h1 style='font-size: 3rem; margin-bottom: 0.5rem;'>🛠️</h1>
            <h2 style='margin-bottom: 0.5rem;'>蕴杰模具全生命周期管理系统</h2>
            <p style='opacity: 0.8; font-size: 1.1rem;'>Die Lifecycle Management System</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 登录表单卡片
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 用户登录")
            st.markdown("---")
            
            username = st.text_input(
                "用户名", 
                key="login_username",
                placeholder="请输入用户名",
                help="输入您的系统用户名"
            )
            
            password = st.text_input(
                "密码", 
                type="password", 
                key="login_password",
                placeholder="请输入密码",
                help="输入您的登录密码"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 登录按钮
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submitted = st.form_submit_button(
                    "🔐 登录系统", 
                    type="primary", 
                    use_container_width=True
                )

            # 处理登录
            if submitted:
                if not username or not password:
                    st.error("❌ 请输入用户名和密码")
                else:
                    with st.spinner("正在验证用户身份..."):
                        try:
                            user_info = login_user(username, password)
                            if user_info:
                                st.success("✅ 登录成功！正在跳转...")
                                # 短暂延迟后刷新页面
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 用户名或密码错误，请重试")
                        except Exception as e:
                            st.error(f"❌ 登录时发生错误：{str(e)}")
                            logger.error(f"登录错误: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 系统信息
        with st.expander("💡 系统信息", expanded=False):
            st.markdown("""
            #### 📋 默认账户信息
            **首次使用请用默认密码登录后立即修改**
            
            | 角色 | 用户名 | 密码 |
            |------|--------|------|
            | 超级管理员 | `admin` | `password123` |
            | 模具库管理员 | `mold_admin` | `password123` |
            | 模具工 | `technician` | `password123` |
            | 冲压操作工 | `operator` | `password123` |
            
            #### 🚀 系统特性
            - 🔒 **安全认证**：多角色权限控制
            - 📊 **全面管理**：模具全生命周期跟踪
            - 🔧 **流程优化**：维修保养智能提醒
            - 📈 **数据洞察**：实时统计和分析报表
            - 🌐 **现代化**：响应式Web界面
            
            #### 📞 技术支持
            **邮箱**：jerry.houyong@gmail.com  
            **版本**：v1.4.0  
            **更新**：2024年6月
            """)

# --- 主界面 ---
def show_main_interface():
    """显示主界面"""
    # 侧边栏用户信息和导航
    setup_sidebar()
    
    # 主内容区域
    setup_main_content()

def setup_sidebar():
    """设置侧边栏"""
    with st.sidebar:
        st.markdown("---")
        
        # 用户信息卡片
        user_name = st.session_state.get('full_name', st.session_state.get('username', '未知用户'))
        user_role = st.session_state.get('user_role', '未知角色')
        
        st.markdown(f"""
        <div class="user-info-card">
            <h3 style='margin: 0; color: white;'>👤 {user_name}</h3>
            <p style='margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;'>🎭 {user_role}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 快速导航
        st.markdown("### 🧭 功能导航")
        
        # 根据角色显示不同的导航选项
        if user_role == '超级管理员':
            show_admin_navigation()
        elif user_role == '模具库管理员':
            show_manager_navigation()
        elif user_role == '模具工':
            show_technician_navigation()
        elif user_role == '冲压操作工':
            show_operator_navigation()
        
        # 通用功能
        st.markdown("---")
        st.markdown("### ⚙️ 系统功能")
        
        if st.button("🏠 返回首页", use_container_width=True):
            # 清除可能的页面状态
            for key in list(st.session_state.keys()):
                if key.startswith('page_'):
                    del st.session_state[key]
            st.rerun()
        
        if st.button("🔄 刷新数据", use_container_width=True):
            st.cache_data.clear()
            st.success("数据已刷新！")
        
        # 登出按钮
        st.markdown("---")
        if st.button("🚪 退出登录", type="secondary", use_container_width=True):
            logout_user()
            st.rerun()

def show_admin_navigation():
    """超级管理员导航"""
    if st.button("👥 用户管理", use_container_width=True):
        st.switch_page("pages/6_用户管理.py")
    if st.button("⚙️ 系统管理", use_container_width=True):
        st.switch_page("pages/5_系统管理.py")
    if st.button("🛠️ 模具管理", use_container_width=True):
        st.switch_page("pages/1_模具管理.py")
    if st.button("📋 借用管理", use_container_width=True):
        st.switch_page("pages/2_借用管理.py")
    if st.button("🔧 维修管理", use_container_width=True):
        st.switch_page("pages/3_维修管理.py")
    if st.button("🔩 部件管理", use_container_width=True):
        st.switch_page("pages/4_部件管理.py")

def show_manager_navigation():
    """模具库管理员导航"""
    if st.button("🛠️ 模具管理", use_container_width=True):
        st.switch_page("pages/1_模具管理.py")
    if st.button("📋 借用管理", use_container_width=True):
        st.switch_page("pages/2_借用管理.py")
    if st.button("🔧 维修管理", use_container_width=True):
        st.switch_page("pages/3_维修管理.py")
    if st.button("🔩 部件管理", use_container_width=True):
        st.switch_page("pages/4_部件管理.py")

def show_technician_navigation():
    """模具工导航"""
    if st.button("🔧 维修管理", use_container_width=True):
        st.switch_page("pages/3_维修管理.py")
    if st.button("🔩 部件管理", use_container_width=True):
        st.switch_page("pages/4_部件管理.py")
    if st.button("🛠️ 模具查询", use_container_width=True):
        st.switch_page("pages/1_模具管理.py")

def show_operator_navigation():
    """冲压操作工导航"""
    if st.button("🛠️ 模具查询", use_container_width=True):
        st.switch_page("pages/1_模具管理.py")
    if st.button("📝 借用申请", use_container_width=True):
        st.switch_page("pages/2_借用管理.py")

def setup_main_content():
    """设置主内容区域"""
    user_name = st.session_state.get('full_name', st.session_state.get('username', '用户'))
    user_role = st.session_state.get('user_role', '未知角色')
    
    # 欢迎消息
    st.markdown(f"""
    <div class="welcome-message">
        <h1 style='margin: 0; color: white;'>🏠 欢迎使用蕴杰模具管理系统</h1>
        <h3 style='margin: 1rem 0 0 0; color: white; opacity: 0.9;'>欢迎回来，{user_name}！</h3>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.8;'>您当前的角色是 <strong>{user_role}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能模块展示
    st.markdown("### 🚀 功能模块")
    show_feature_cards(user_role)
    
    # 系统状态概览
    st.markdown("### 📊 系统概览")
    show_system_overview()
    
    # 快速操作面板
    show_quick_actions(user_role)

def show_feature_cards(user_role):
    """显示功能模块卡片"""
    # 根据角色显示不同的功能卡片
    if user_role == '超级管理员':
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>👥</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>用户管理</h3>
                <p style='margin: 0; opacity: 0.9;'>管理系统用户账户和权限分配</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>⚙️</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>系统管理</h3>
                <p style='margin: 0; opacity: 0.9;'>系统配置、监控和维护</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>🛠️</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>模具管理</h3>
                <p style='margin: 0; opacity: 0.9;'>模具台账和生命周期管理</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif user_role == '模具库管理员':
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>🛠️</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>模具管理</h3>
                <p style='margin: 0; opacity: 0.9;'>模具台账、状态和位置管理</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>📋</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>借用管理</h3>
                <p style='margin: 0; opacity: 0.9;'>借用申请审批和流程管理</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif user_role == '模具工':
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>🔧</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>维修管理</h3>
                <p style='margin: 0; opacity: 0.9;'>维修任务执行和记录管理</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                         color: #333; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: #333; margin: 0; font-size: 2rem;'>🔩</h2>
                <h3 style='color: #333; margin: 0.5rem 0;'>部件管理</h3>
                <p style='margin: 0; opacity: 0.8;'>模具部件和压边圈管理</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif user_role == '冲压操作工':
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); 
                         color: #333; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: #333; margin: 0; font-size: 2rem;'>🔍</h2>
                <h3 style='color: #333; margin: 0.5rem 0;'>模具查询</h3>
                <p style='margin: 0; opacity: 0.8;'>查看模具信息和使用状态</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='feature-card' style='background: linear-gradient(135deg, #a8caba 0%, #5d4e75 100%); 
                         color: white; padding: 2rem; border-radius: 12px; text-align: center;'>
                <h2 style='color: white; margin: 0; font-size: 2rem;'>📝</h2>
                <h3 style='color: white; margin: 0.5rem 0;'>借用申请</h3>
                <p style='margin: 0; opacity: 0.9;'>提交和跟踪模具借用申请</p>
            </div>
            """, unsafe_allow_html=True)

def show_system_overview():
    """显示系统状态概览"""
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                total_molds = execute_query("SELECT COUNT(*) as count FROM molds", fetch_one=True)
                count = total_molds['count'] if total_molds else 0
                st.markdown(f"""
                <div class="metric-container">
                    <h2 style='color: #1f77b4; margin: 0; font-size: 2rem;'>{count}</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>模具总数</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"获取模具总数失败: {e}")
                st.markdown("""
                <div class="metric-container">
                    <h2 style='color: #999; margin: 0; font-size: 2rem;'>--</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>模具总数</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            try:
                active_loans = execute_query(
                    """SELECT COUNT(*) as count FROM mold_loan_records 
                       WHERE loan_status_id IN (
                           SELECT status_id FROM loan_statuses 
                           WHERE status_name IN ('已借出', '已批准')
                       )""", 
                    fetch_one=True
                )
                count = active_loans['count'] if active_loans else 0
                st.markdown(f"""
                <div class="metric-container">
                    <h2 style='color: #ff6b6b; margin: 0; font-size: 2rem;'>{count}</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>当前借用</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"获取当前借用失败: {e}")
                st.markdown("""
                <div class="metric-container">
                    <h2 style='color: #999; margin: 0; font-size: 2rem;'>--</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>当前借用</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            try:
                maintenance_count = execute_query(
                    "SELECT COUNT(*) as count FROM mold_maintenance_logs WHERE maintenance_end_timestamp IS NULL", 
                    fetch_one=True
                )
                count = maintenance_count['count'] if maintenance_count else 0
                st.markdown(f"""
                <div class="metric-container">
                    <h2 style='color: #4ecdc4; margin: 0; font-size: 2rem;'>{count}</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>维修中</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"获取维修中失败: {e}")
                st.markdown("""
                <div class="metric-container">
                    <h2 style='color: #999; margin: 0; font-size: 2rem;'>--</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>维修中</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            try:
                active_users = execute_query("SELECT COUNT(*) as count FROM users WHERE is_active = true", fetch_one=True)
                count = active_users['count'] if active_users else 0
                st.markdown(f"""
                <div class="metric-container">
                    <h2 style='color: #45b7d1; margin: 0; font-size: 2rem;'>{count}</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>活跃用户</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"获取活跃用户失败: {e}")
                st.markdown("""
                <div class="metric-container">
                    <h2 style='color: #999; margin: 0; font-size: 2rem;'>--</h2>
                    <p style='margin: 0.5rem 0 0 0; color: #666;'>活跃用户</p>
                </div>
                """, unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"系统概览加载失败: {e}")
        st.warning("📊 系统概览数据加载中...")

def show_quick_actions(user_role):
    """显示快速操作面板"""
    st.markdown("---")
    st.markdown("### ⚡ 快速操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 系统状态", use_container_width=True):
            show_system_status()
    
    with col2:
        if st.button("📈 数据统计", use_container_width=True):
            show_data_statistics()
    
    with col3:
        if st.button("🔍 搜索功能", use_container_width=True):
            show_search_interface()
    
    with col4:
        if st.button("❓ 帮助文档", use_container_width=True):
            show_help_documentation()

def show_system_status():
    """显示系统状态详情"""
    with st.expander("🖥️ 系统状态详情", expanded=True):
        try:
            # 数据库连接状态
            db_status = test_connection()
            status_color = "🟢" if db_status else "🔴"
            status_text = "正常" if db_status else "异常"
            
            st.markdown(f"**数据库连接**: {status_color} {status_text}")
            
            # 系统运行时间（模拟）
            uptime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"**当前时间**: {uptime}")
            
            # 版本信息
            st.markdown("**系统版本**: v1.4.0")
            st.markdown("**最后更新**: 2024年6月")
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            st.error(f"获取系统状态时出错: {e}")

def show_data_statistics():
    """显示数据统计详情"""
    with st.expander("📈 数据统计详情", expanded=True):
        try:
            # 模具状态分布
            st.markdown("**模具状态分布:**")
            mold_status_query = """
            SELECT ms.status_name, COUNT(m.mold_id) as count
            FROM mold_statuses ms
            LEFT JOIN molds m ON ms.status_id = m.current_status_id
            GROUP BY ms.status_id, ms.status_name
            ORDER BY count DESC
            """
            
            mold_stats = execute_query(mold_status_query, fetch_all=True)
            if mold_stats:
                for stat in mold_stats:
                    st.markdown(f"- {stat['status_name']}: {stat['count']} 个")
            else:
                st.info("暂无模具状态数据")
            
            # 本月活动统计
            st.markdown("**本月活动统计:**")
            monthly_stats = execute_query("""
                SELECT 
                    COUNT(CASE WHEN action_type = 'LOGIN' THEN 1 END) as logins,
                    COUNT(CASE WHEN action_type LIKE 'CREATE%' THEN 1 END) as creations,
                    COUNT(CASE WHEN action_type LIKE '%LOAN%' THEN 1 END) as loan_actions
                FROM system_logs 
                WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
            """, fetch_one=True)
            
            if monthly_stats:
                st.markdown(f"- 登录次数: {monthly_stats['logins']}")
                st.markdown(f"- 创建操作: {monthly_stats['creations']}")
                st.markdown(f"- 借用操作: {monthly_stats['loan_actions']}")
            else:
                st.info("暂无本月活动统计")
            
        except Exception as e:
            logger.error(f"获取数据统计失败: {e}")
            st.error(f"获取数据统计时出错: {e}")

def show_search_interface():
    """显示搜索界面"""
    with st.expander("🔍 全局搜索", expanded=True):
        search_term = st.text_input("搜索模具、用户或记录", placeholder="输入关键词...")
        
        if search_term:
            try:
                # 搜索模具
                mold_results = execute_query(
                    "SELECT mold_code, mold_name FROM molds WHERE mold_code ILIKE %s OR mold_name ILIKE %s LIMIT 5",
                    params=(f"%{search_term}%", f"%{search_term}%"),
                    fetch_all=True
                )
                
                if mold_results:
                    st.markdown("**模具搜索结果:**")
                    for mold in mold_results:
                        st.markdown(f"- {mold['mold_code']}: {mold['mold_name']}")
                
                # 搜索用户（如果有权限）
                if st.session_state.get('user_role') in ['超级管理员', '模具库管理员']:
                    user_results = execute_query(
                        "SELECT username, full_name FROM users WHERE username ILIKE %s OR full_name ILIKE %s LIMIT 3",
                        params=(f"%{search_term}%", f"%{search_term}%"),
                        fetch_all=True
                    )
                    
                    if user_results:
                        st.markdown("**用户搜索结果:**")
                        for user in user_results:
                            st.markdown(f"- {user['username']}: {user['full_name']}")
                
            except Exception as e:
                logger.error(f"搜索失败: {e}")
                st.error(f"搜索时出错: {e}")

def show_help_documentation():
    """显示帮助文档"""
    with st.expander("📖 帮助文档", expanded=True):
        user_role = st.session_state.get('user_role', '')
        
        st.markdown(f"""
        ### 🎯 {user_role} 操作指南
        
        #### 📋 基本操作
        1. **导航菜单**: 使用左侧边栏进行功能模块切换
        2. **数据刷新**: 点击"刷新数据"按钮获取最新信息
        3. **搜索功能**: 使用全局搜索快速定位信息
        
        #### 🔐 安全提醒
        - 首次登录后请立即修改默认密码
        - 定期更换密码以确保账户安全
        - 退出时请点击"退出登录"按钮
        
        #### 🆘 常见问题
        
        **Q: 忘记密码怎么办？**
        A: 请联系系统管理员重置密码
        
        **Q: 页面加载缓慢怎么办？**
        A: 点击"刷新数据"按钮或联系技术支持
        
        **Q: 权限不足怎么办？**
        A: 确认您的角色权限，或联系管理员分配相应权限
        
        #### 📞 技术支持
        - **邮箱**: jerry.houyong@gmail.com
        - **版本**: v1.4.0
        - **更新日期**: 2024年6月25日
        
        #### 🚀 新功能预告
        - 移动端适配优化
        - 高级数据分析报表
        - 自动化工作流程
        - 多语言支持
        """)

def show_recent_activities():
    """显示最近活动"""
    st.markdown("#### 📅 最近活动")
    
    try:
        recent_logs = execute_query("""
            SELECT 
                sl.action_type,
                sl.target_resource,
                sl.timestamp,
                u.full_name,
                u.username
            FROM system_logs sl
            LEFT JOIN users u ON sl.user_id = u.user_id
            ORDER BY sl.timestamp DESC
            LIMIT 8
        """, fetch_all=True)
        
        if recent_logs:
            for i, log in enumerate(recent_logs):
                # 操作类型映射
                action_map = {
                    'LOGIN': '🔐 用户登录',
                    'LOGOUT': '🚪 用户登出',
                    'CREATE_MOLD': '➕ 创建模具',
                    'CREATE_LOAN': '📝 创建借用',
                    'CREATE_MAINTENANCE': '🔧 创建维修',
                    'UPDATE_MOLD': '✏️ 更新模具',
                    'APPROVE_LOAN': '✅ 批准借用',
                    'REJECT_LOAN': '❌ 驳回借用'
                }
                
                action_display = action_map.get(log['action_type'], f"📋 {log['action_type']}")
                user_name = log['full_name'] or log['username'] or '系统'
                time_str = log['timestamp'].strftime('%m-%d %H:%M')
                
                # 使用颜色区分不同类型的操作
                if 'CREATE' in log['action_type']:
                    color = "#4CAF50"  # 绿色
                elif 'LOGIN' in log['action_type']:
                    color = "#2196F3"  # 蓝色
                elif 'DELETE' in log['action_type']:
                    color = "#F44336"  # 红色
                else:
                    color = "#FF9800"  # 橙色
                
                st.markdown(f"""
                <div class="activity-item" style="border-left-color: {color};">
                    <strong>{time_str}</strong> {user_name} {action_display}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📋 暂无最近活动记录")
            
    except Exception as e:
        logger.error(f"获取最近活动失败: {e}")
        st.info("📋 活动日志加载中...")

# --- 主程序入口 ---
def main():
    """主程序入口"""
    # 加载自定义样式
    load_custom_css()
    
    # 初始化会话状态
    init_session_state()
    
    # 检查登录状态
    if not st.session_state.get('logged_in', False):
        show_login_form()
    else:
        show_main_interface()
        
        # 在主界面底部显示最近活动
        st.markdown("---")
        show_recent_activities()
        
        # 页脚信息
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style='text-align: center; color: #666; padding: 1rem;'>
                <p style='margin: 0;'>🛠️ 蕴杰模具全生命周期管理系统 v1.4.0</p>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>
                    © 2024 蕴杰金属 | 技术支持: jerry.houyong@gmail.com
                </p>
            </div>
            """, unsafe_allow_html=True)

# --- 运行主程序 ---
if __name__ == "__main__":
    main()