# app/utils/ui.py — 全局 UI 样式与公共组件
"""
统一样式标准：
  主色  #1a56db（蓝）
  紫色  #7e3af2
  成功  #057a55（绿）
  警告  #c27803（琥珀）
  危险  #c81e1e（红）
  灰字  #6b7280
  背景  #f1f5f9
  卡片  #ffffff
"""
import streamlit as st

# ── 品牌色 ─────────────────────────────────────────────────────────
PRIMARY  = "#1a56db"
PURPLE   = "#7e3af2"
SUCCESS  = "#057a55"
WARNING  = "#c27803"
DANGER   = "#c81e1e"
NEUTRAL  = "#6b7280"
BG       = "#f1f5f9"
CARD     = "#ffffff"

# ── 全局 CSS（注入一次即生效于整个页面） ───────────────────────────
_GLOBAL_CSS = """
<style>
/* ── Streamlit 原生页面导航隐藏（消除双导航） ── */
[data-testid="stSidebarNav"]          { display: none !important; }
[data-testid="stSidebarNavSeparator"] { display: none !important; }

/* ── 整体背景 ── */
.stApp { background-color: #f1f5f9; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; }

/* ── 页面头部横幅 ── */
.page-banner {
    background: linear-gradient(90deg, #1a56db 0%, #7e3af2 100%);
    color: white;
    padding: 1rem 1.4rem 0.9rem;
    border-radius: 10px;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 8px rgba(26,86,219,.25);
}
.page-banner h1 {
    color: white !important;
    margin: 0 0 0.15rem 0;
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}
.page-banner p {
    color: rgba(255,255,255,0.82);
    margin: 0;
    font-size: 0.85rem;
}

/* ── 统计卡片 ── */
.stat-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 1.1rem 1.2rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    border-top: 3px solid #1a56db;
    margin-bottom: .5rem;
}
.stat-card .stat-val {
    font-size: 1.9rem;
    font-weight: 700;
    color: #1a56db;
    line-height: 1.2;
    margin-bottom: .2rem;
}
.stat-card .stat-lbl {
    font-size: .78rem;
    color: #6b7280;
    font-weight: 500;
}

/* ── 内容卡片 ── */
.content-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    margin-bottom: 1rem;
}

/* ── 侧边栏用户信息卡 ── */
.sidebar-user-card {
    background: linear-gradient(135deg, #1a56db 0%, #7e3af2 100%);
    color: white;
    padding: 1.1rem 1rem;
    border-radius: 10px;
    text-align: center;
    margin-bottom: .5rem;
}
.sidebar-user-card .u-name {
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 .2rem 0;
}
.sidebar-user-card .u-role {
    font-size: .8rem;
    opacity: .88;
    margin: 0;
}

/* ── 活动日志条目 ── */
.activity-row {
    background: #fff;
    border-left: 3px solid #1a56db;
    border-radius: 6px;
    padding: .55rem .85rem;
    margin-bottom: .35rem;
    font-size: .85rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}

/* ── 登录卡片 ── */
.login-wrapper {
    background: white;
    border-radius: 14px;
    padding: 2rem 2.2rem 1.8rem;
    box-shadow: 0 8px 28px rgba(0,0,0,.11);
    margin: 1.2rem 0 1rem;
}

/* ── 按钮通用 ── */
.stButton > button {
    border-radius: 7px;
    font-weight: 600;
    transition: box-shadow .2s ease, transform .15s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,.13);
}

/* ── 输入框 ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 7px !important;
}

/* ── 表格 ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── 通用分割线文字 ── */
.section-title {
    font-size: .9rem;
    font-weight: 600;
    color: #374151;
    margin: 1rem 0 .5rem 0;
    padding-bottom: .25rem;
    border-bottom: 2px solid #e5e7eb;
}

/* ── 隐藏默认 Streamlit 顶栏 / 页脚 ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
</style>
"""


def inject_global_css() -> None:
    """在当前页面注入全局 CSS（每个页面顶部调用一次）。"""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    """渲染统一风格的页面横幅标题。"""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""<div class="page-banner">
              <h1>{icon} {title}</h1>
              {sub_html}
            </div>""",
        unsafe_allow_html=True,
    )


def stat_card(value, label: str, color: str = PRIMARY) -> None:
    """渲染单个统计数字卡片（用于 st.columns 内部）。"""
    st.markdown(
        f"""<div class="stat-card" style="border-top-color:{color};">
              <div class="stat-val" style="color:{color};">{value}</div>
              <div class="stat-lbl">{label}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    """渲染小节标题（带下划线）。"""
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def activity_row(time_str: str, user: str, action: str, color: str = PRIMARY) -> None:
    """渲染一条活动日志条目。"""
    st.markdown(
        f"""<div class="activity-row" style="border-left-color:{color};">
              <strong>{time_str}</strong>&nbsp;&nbsp;{user}&nbsp;{action}
            </div>""",
        unsafe_allow_html=True,
    )
