# app/utils/nav.py — 导航结构与共享侧边栏
"""
统一管理角色→页面的映射关系，以及所有页面共享的侧边栏组件。
每个子页面只需在 login 校验通过后调用一次 setup_sidebar() 即可。
"""
import streamlit as st

# ── 角色导航映射（label, page_path）────────────────────────────────
NAV = {
    '超级管理员': [
        ("🛠️ 模具管理", "pages/1_模具管理.py"),
        ("📋 借用管理", "pages/2_借用管理.py"),
        ("🔧 维修管理", "pages/3_维修管理.py"),
        ("🔩 部件管理", "pages/4_部件管理.py"),
        ("⚙️ 系统管理", "pages/5_系统管理.py"),
        ("🤖 模具推荐", "pages/6_模具推荐.py"),
        ("💰 成本分析", "pages/7_成本分析.py"),
        ("📅 生产排程", "pages/8_生产排程.py"),
    ],
    '模具库管理员': [
        ("🛠️ 模具管理", "pages/1_模具管理.py"),
        ("📋 借用管理", "pages/2_借用管理.py"),
        ("🔧 维修管理", "pages/3_维修管理.py"),
        ("🔩 部件管理", "pages/4_部件管理.py"),
        ("🤖 模具推荐", "pages/6_模具推荐.py"),
        ("💰 成本分析", "pages/7_成本分析.py"),
        ("📅 生产排程", "pages/8_生产排程.py"),
    ],
    '模具工': [
        ("🛠️ 模具管理", "pages/1_模具管理.py"),
        ("🔧 维修管理", "pages/3_维修管理.py"),
        ("🔩 部件管理", "pages/4_部件管理.py"),
    ],
    '冲压操作工': [
        ("🛠️ 模具管理", "pages/1_模具管理.py"),
        ("📝 借用申请", "pages/2_借用管理.py"),
    ],
}


def nav_buttons(role: str, current_page: str = "") -> None:
    """渲染角色对应的导航按钮列表。

    current_page: 当前页面文件名（如 '1_模具管理.py'），用于高亮当前项。
    """
    for label, page in NAV.get(role, []):
        is_current = current_page and current_page in page
        btn_type = "primary" if is_current else "secondary"
        if st.button(
            label,
            use_container_width=True,
            key=f"nav_{label}",
            type=btn_type,
        ):
            st.switch_page(page)


def setup_sidebar(current_page: str = "") -> None:
    """渲染完整侧边栏：用户信息卡 + 功能导航 + 系统操作。

    在每个子页面完成 login 校验后立即调用此函数。
    current_page 传入当前页面文件名可高亮当前菜单项。
    """
    role = st.session_state.get('user_role', '')
    name = st.session_state.get('full_name') or st.session_state.get('username', '未知')

    with st.sidebar:
        # ── 用户信息卡 ────────────────────────────────────────────
        st.markdown(f"""
        <div class="sidebar-user-card">
            <div class="u-name">👤 {name}</div>
            <div class="u-role">🎭 {role}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── 功能导航 ──────────────────────────────────────────────
        st.markdown("**🧭 功能模块**")
        nav_buttons(role, current_page)

        st.divider()

        # ── 系统操作 ──────────────────────────────────────────────
        st.markdown("**⚙️ 系统**")
        if st.button("🏠 首页", use_container_width=True, key="sidebar_home"):
            st.switch_page("main.py")
        if st.button("🔄 刷新缓存", use_container_width=True, key="sidebar_refresh"):
            st.cache_data.clear()
            st.toast("缓存已清除", icon="✅")
        st.divider()
        if st.button("🚪 退出登录", type="secondary",
                     use_container_width=True, key="sidebar_logout"):
            from utils.auth import logout_user  # 懒加载，避免循环 / mock 冲突
            logout_user()
            st.switch_page("main.py")
