# app/main.py
import streamlit as st
from utils.auth import login_user, logout_user, restore_session
from utils.database import execute_query, ensure_database_initialized, test_connection
from utils.ui import inject_global_css, page_header, stat_card, activity_row, PURPLE, SUCCESS, WARNING, DANGER
from utils.nav import NAV, nav_buttons, setup_sidebar
import logging
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 页面配置（全局，仅此处设置）────────────────────────────────────
st.set_page_config(
    page_title="蕴杰模具管理系统",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 会话初始化 ───────────────────────────────────────────────────────
def _init_session():
    defaults = {
        'logged_in': False, 'username': '',
        'user_role': '', 'user_id': None, 'full_name': '',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════
# 登录页
# ══════════════════════════════════════════════════════════════════════
def show_login_page():
    # 居中布局
    _, col, _ = st.columns([1, 2, 1])
    with col:
        # ── 标题 ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center; padding: 1.5rem 0 .8rem;">
            <div style="font-size:3rem; line-height:1.1;">🛠️</div>
            <h2 style="margin:.4rem 0 .15rem; color:#1a56db; font-weight:700;">
                蕴杰模具全生命周期管理系统
            </h2>
            <p style="color:#6b7280; font-size:.9rem; margin:0;">
                Die Lifecycle Management System
            </p>
        </div>
        """, unsafe_allow_html=True)

        # ── 登录表单（无 div 包装，避免空白框）──────────────────────
        with st.container():
            with st.form("login_form", clear_on_submit=False):
                st.markdown("#### 🔐 用户登录")
                st.divider()

                username = st.text_input(
                    "用户名", placeholder="请输入用户名",
                    key="login_username"
                )
                password = st.text_input(
                    "密码", type="password", placeholder="请输入密码",
                    key="login_password"
                )
                st.markdown("<br>", unsafe_allow_html=True)

                _, btn_col, _ = st.columns([1, 2, 1])
                with btn_col:
                    submitted = st.form_submit_button(
                        "🔐 登 录", type="primary", use_container_width=True
                    )

                if submitted:
                    if not username or not password:
                        st.error("❌ 请输入用户名和密码")
                    else:
                        with st.spinner("正在验证…"):
                            try:
                                user_info = login_user(username, password)
                                if user_info:
                                    st.success("✅ 登录成功！")
                                    st.rerun()
                                else:
                                    st.error("❌ 用户名或密码错误")
                            except Exception as e:
                                st.error(f"❌ 登录异常：{e}")
                                logger.error(f"登录错误: {e}")

        # ── 系统说明折叠框 ──────────────────────────────────────────
        with st.expander("💡 系统信息", expanded=False):
            st.markdown("""
            **系统特性**
            🔒 多角色权限控制 · 📊 全生命周期追踪 · 🔧 智能维修提醒
            📈 实时数据统计 · 🌐 现代化 Web 界面

            **默认管理员账号**：`admin`（首次登录后请立即修改密码）
            **忘记密码**：联系系统管理员重置
            **技术支持**：jerry.houyong@gmail.com · v1.4.0
            """)

# setup_sidebar / nav_buttons / NAV 已移至 utils/nav.py，此处直接使用导入的版本
# _NAV 保留以兼容测试（test_main_navigation.py 读取 module._NAV）
_NAV = NAV

# ══════════════════════════════════════════════════════════════════════
# 主仪表板
# ══════════════════════════════════════════════════════════════════════
def show_dashboard():
    role = st.session_state.get('user_role', '')
    name = st.session_state.get('full_name') or st.session_state.get('username', '用户')

    page_header("🏠", "蕴杰模具管理系统", f"欢迎回来，{name}！当前角色：{role}")

    # ── 统计概览 ─────────────────────────────────────────────────────
    _show_stats()

    st.divider()

    # ── 功能入口卡片 ─────────────────────────────────────────────────
    _show_module_cards(role)

    st.divider()

    # ── 快速操作 ─────────────────────────────────────────────────────
    _show_quick_actions()

    st.divider()

    # ── 最近活动 ─────────────────────────────────────────────────────
    _show_recent_activities()

    # ── 页脚 ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;color:#9ca3af;padding:.8rem 0;font-size:.8rem;">
        🛠️ 蕴杰模具全生命周期管理系统 v1.4.0 ·
        © 2024 蕴杰金属 · jerry.houyong@gmail.com
    </div>
    """, unsafe_allow_html=True)


def _show_stats():
    c1, c2, c3, c4 = st.columns(4)
    queries = [
        ("SELECT COUNT(*) AS n FROM molds",                               "模具总数",  "#1a56db"),
        ("""SELECT COUNT(*) AS n FROM mold_loan_records mlr
            JOIN loan_statuses ls ON mlr.loan_status_id=ls.status_id
            WHERE ls.status_name IN ('已借出','已批准')""",               "当前借出",  DANGER),
        ("""SELECT COUNT(*) AS n FROM mold_maintenance_logs
            WHERE maintenance_end_timestamp IS NULL""",                   "维修中",    WARNING),
        ("SELECT COUNT(*) AS n FROM users WHERE is_active=1",             "活跃用户",  SUCCESS),
    ]
    for col, (sql, label, color) in zip([c1, c2, c3, c4], queries):
        with col:
            try:
                row = execute_query(sql, fetch_one=True)
                val = row['n'] if row else "--"
            except Exception:
                val = "--"
            stat_card(val, label, color)


# 功能模块定义（label, icon, desc, page, grad）
_ALL_MODULES = [
    ("模具管理",  "🛠️", "模具台账与生命周期管理", "pages/1_模具管理.py",
     "linear-gradient(135deg,#1a56db,#7e3af2)"),
    ("借用管理",  "📋", "借用申请审批与流程",      "pages/2_借用管理.py",
     "linear-gradient(135deg,#0694a2,#1c64f2)"),
    ("维修管理",  "🔧", "维修保养任务与记录",      "pages/3_维修管理.py",
     "linear-gradient(135deg,#057a55,#0e9f6e)"),
    ("部件管理",  "🔩", "模具部件与压边圈管理",    "pages/4_部件管理.py",
     "linear-gradient(135deg,#5850ec,#7e3af2)"),
    ("系统管理",  "⚙️", "用户与系统配置",          "pages/5_系统管理.py",
     "linear-gradient(135deg,#c27803,#d97706)"),
    ("模具推荐",  "🤖", "智能模具推荐算法",        "pages/6_模具推荐.py",
     "linear-gradient(135deg,#0694a2,#06b6d4)"),
    ("成本分析",  "💰", "成本统计与分析仪表板",    "pages/7_成本分析.py",
     "linear-gradient(135deg,#9f580a,#c27803)"),
    ("生产排程",  "📅", "生产计划与排程管理",      "pages/8_生产排程.py",
     "linear-gradient(135deg,#1a56db,#0694a2)"),
]

_ROLE_MODULES = {
    '超级管理员':  [0,1,2,3,4,5,6,7],
    '模具库管理员':[0,1,2,3,5,6,7],
    '模具工':      [0,2,3],
    '冲压操作工':  [0,1],
}

def _show_module_cards(role: str):
    st.markdown("#### 🚀 功能模块")
    indices = _ROLE_MODULES.get(role, [0])
    modules = [_ALL_MODULES[i] for i in indices]
    cols = st.columns(min(4, len(modules)))
    for i, (label, icon, desc, page, grad) in enumerate(modules):
        with cols[i % len(cols)]:
            st.markdown(f"""
            <div style="background:{grad};color:white;border-radius:10px;
                        padding:1.1rem 1rem;text-align:center;margin-bottom:.5rem;
                        box-shadow:0 2px 8px rgba(0,0,0,.15);">
              <div style="font-size:1.8rem;line-height:1;">{icon}</div>
              <div style="font-weight:700;font-size:.95rem;margin:.35rem 0 .2rem;">{label}</div>
              <div style="font-size:.75rem;opacity:.88;">{desc}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"进入 {label}", key=f"mod_{label}", use_container_width=True):
                st.switch_page(page)


def _show_quick_actions():
    st.markdown("#### ⚡ 快速操作")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("📊 系统状态", use_container_width=True):
            st.session_state['_qa'] = 'status'
    with c2:
        if st.button("📈 数据统计", use_container_width=True):
            st.session_state['_qa'] = 'stats'
    with c3:
        if st.button("🔍 模具搜索", use_container_width=True):
            st.session_state['_qa'] = 'search'
    with c4:
        if st.button("❓ 帮助", use_container_width=True):
            st.session_state['_qa'] = 'help'

    qa = st.session_state.get('_qa')
    if qa == 'status':
        _panel_system_status()
    elif qa == 'stats':
        _panel_data_stats()
    elif qa == 'search':
        _panel_search()
    elif qa == 'help':
        _panel_help()


def _panel_system_status():
    with st.expander("🖥️ 系统状态", expanded=True):
        ok = test_connection()
        st.markdown(f"**数据库**: {'🟢 正常' if ok else '🔴 异常'}")
        st.markdown(f"**当前时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("**版本**: v1.4.0")


def _panel_data_stats():
    with st.expander("📈 数据统计", expanded=True):
        try:
            stats = execute_query("""
                SELECT ms.status_name, COUNT(m.mold_id) AS cnt
                FROM mold_statuses ms
                LEFT JOIN molds m ON ms.status_id = m.current_status_id
                GROUP BY ms.status_id, ms.status_name
                ORDER BY cnt DESC
            """, fetch_all=True)
            if stats:
                st.markdown("**模具状态分布**")
                for s in stats:
                    st.markdown(f"- {s['status_name']}：{s['cnt']} 个")
            # 本月活动
            monthly = execute_query("""
                SELECT
                    COUNT(CASE WHEN action_type='LOGIN' THEN 1 END) AS logins,
                    COUNT(CASE WHEN action_type LIKE 'CREATE%' THEN 1 END) AS creates,
                    COUNT(CASE WHEN action_type LIKE '%LOAN%' THEN 1 END) AS loans
                FROM system_logs
                WHERE timestamp >= date('now','start of month')
            """, fetch_one=True)
            if monthly:
                st.markdown("**本月活动**")
                st.markdown(f"- 登录：{monthly['logins']} 次 · 创建：{monthly['creates']} 次 · 借用：{monthly['loans']} 次")
        except Exception as e:
            st.warning(f"统计数据加载失败：{e}")


def _panel_search():
    with st.expander("🔍 模具快速搜索", expanded=True):
        kw = st.text_input("输入编号或名称关键词", placeholder="如：MD-001 或 拉延模")
        if kw:
            try:
                results = execute_query(
                    "SELECT mold_code, mold_name FROM molds "
                    "WHERE mold_code LIKE %s OR mold_name LIKE %s LIMIT 10",
                    params=(f"%{kw}%", f"%{kw}%"), fetch_all=True
                )
                if results:
                    for r in results:
                        st.markdown(f"- **{r['mold_code']}** — {r['mold_name']}")
                else:
                    st.info("未找到匹配记录")
            except Exception as e:
                st.error(f"搜索失败：{e}")


def _panel_help():
    with st.expander("📖 帮助文档", expanded=True):
        role = st.session_state.get('user_role', '')
        st.markdown(f"""
**{role} 操作指南**

1. **导航**：使用左侧边栏按钮切换功能模块
2. **刷新**：点击侧边栏"刷新缓存"获取最新数据
3. **搜索**：各列表页顶部均提供筛选搜索

**安全提醒**
首次登录请修改默认密码 · 使用完毕请点击"退出登录"

**技术支持**：jerry.houyong@gmail.com · v1.4.0
""")


def _show_recent_activities():
    st.markdown("#### 📅 最近操作记录")
    try:
        logs = execute_query("""
            SELECT sl.action_type, sl.timestamp,
                   COALESCE(u.full_name, u.username, '系统') AS uname
            FROM system_logs sl
            LEFT JOIN users u ON sl.user_id = u.user_id
            ORDER BY sl.timestamp DESC LIMIT 8
        """, fetch_all=True)

        ACTION_MAP = {
            'LOGIN': ('🔐 登录系统', '#1a56db'),
            'LOGOUT': ('🚪 退出系统', '#6b7280'),
            'CREATE_MOLD': ('➕ 新增模具', '#057a55'),
            'UPDATE_MOLD': ('✏️ 更新模具', '#c27803'),
            'CREATE_LOAN': ('📝 创建借用', '#7e3af2'),
            'APPROVE_LOAN': ('✅ 批准借用', '#057a55'),
            'REJECT_LOAN': ('❌ 驳回借用', '#c81e1e'),
            'CREATE_MAINTENANCE': ('🔧 创建维修', '#0694a2'),
        }

        if logs:
            for log in logs:
                ts = log['timestamp']
                try:
                    import pandas as pd
                    ts_str = pd.to_datetime(ts).strftime('%m-%d %H:%M') if ts else '--'
                except Exception:
                    ts_str = str(ts)[:16] if ts else '--'
                label, color = ACTION_MAP.get(log['action_type'],
                                              (f"📋 {log['action_type']}", '#6b7280'))
                activity_row(ts_str, log['uname'], label, color)
        else:
            st.info("📋 暂无活动记录")
    except Exception as e:
        logger.error(f"活动日志加载失败: {e}")
        st.info("📋 活动日志加载中…")


# ══════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════
def main():
    inject_global_css()
    if not ensure_database_initialized():
        st.error("❌ 数据库初始化失败，请检查 SQLite 路径和初始化脚本。")
        st.stop()

    _init_session()
    restore_session()  # 刷新页面后从 URL 令牌恢复登录态

    if not st.session_state.get('logged_in'):
        show_login_page()
    else:
        setup_sidebar()
        show_dashboard()


main()
