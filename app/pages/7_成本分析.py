# pages/7_成本分析.py
#
# 成本分析仪表板 — 全部基于真实数据（维修保养记录中登记的费用与起止时间）。
# 2026-06-11 起移除全部演示数据：此前概览/明细/停机/优化建议为硬编码样例，
# 会误导管理决策；cost_records 表无录入入口，不再作为数据源。
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
from utils.database import execute_query
from utils.auth import require_permission
from utils.ui import inject_global_css, page_header
from utils.nav import setup_sidebar

# 费用/停机的归属日期：优先取保养结束时间，其次开始时间，最后记录创建时间
_COST_DATE_EXPR = "DATE(COALESCE(ml.maintenance_end_timestamp, ml.maintenance_start_timestamp, ml.created_at))"


# ── SQL 构建（全部聚合自 mold_maintenance_logs，可独立测试）──────────
def _build_cost_summary_query():
    return f"""
    SELECT
        COALESCE(SUM(ml.cost), 0) AS total_cost,
        COUNT(*) AS maintenance_count,
        COUNT(DISTINCT ml.mold_id) AS mold_count
    FROM mold_maintenance_logs ml
    WHERE {_COST_DATE_EXPR} BETWEEN %s AND %s
    """


def _build_cost_trend_query():
    return f"""
    SELECT
        {_COST_DATE_EXPR} AS date,
        COALESCE(SUM(ml.cost), 0) AS total_cost,
        COUNT(*) AS maintenance_count
    FROM mold_maintenance_logs ml
    WHERE {_COST_DATE_EXPR} BETWEEN %s AND %s
    GROUP BY {_COST_DATE_EXPR}
    ORDER BY date
    """


def _build_cost_composition_query():
    return f"""
    SELECT
        COALESCE(mt.type_name, '未分类') AS cost_type,
        COALESCE(SUM(ml.cost), 0) AS total_amount,
        COUNT(*) AS cnt
    FROM mold_maintenance_logs ml
    LEFT JOIN maintenance_types mt ON ml.maintenance_type_id = mt.type_id
    WHERE {_COST_DATE_EXPR} BETWEEN %s AND %s
    GROUP BY COALESCE(mt.type_name, '未分类')
    ORDER BY total_amount DESC
    """


_MOLD_COST_SORTS = {
    "总费用降序": "total_cost DESC",
    "总费用升序": "total_cost ASC",
    "维修次数降序": "maintenance_count DESC",
}


def _build_mold_cost_details_query(repair_filter=None, sort_by="总费用降序"):
    """repair_filter: None=全部, 1=仅维修, 0=仅保养（maintenance_types.is_repair）"""
    where = f"WHERE {_COST_DATE_EXPR} BETWEEN %s AND %s"
    if repair_filter is not None:
        where += " AND mt.is_repair = %s"
    order = _MOLD_COST_SORTS.get(sort_by, "total_cost DESC")
    return f"""
    SELECT
        m.mold_code,
        m.mold_name,
        COALESCE(SUM(ml.cost), 0) AS total_cost,
        COUNT(*) AS maintenance_count,
        COALESCE(AVG(ml.cost), 0) AS avg_cost
    FROM mold_maintenance_logs ml
    JOIN molds m ON ml.mold_id = m.mold_id
    LEFT JOIN maintenance_types mt ON ml.maintenance_type_id = mt.type_id
    {where}
    GROUP BY ml.mold_id, m.mold_code, m.mold_name
    ORDER BY {order}
    LIMIT %s
    """


def _build_downtime_query():
    """停机时长 = 维修起止时间差（小时）；未填写结束时间的记录不计入。"""
    return f"""
    SELECT
        m.mold_code,
        m.mold_name,
        {_COST_DATE_EXPR} AS date,
        (julianday(ml.maintenance_end_timestamp) - julianday(ml.maintenance_start_timestamp)) * 24 AS hours
    FROM mold_maintenance_logs ml
    JOIN molds m ON ml.mold_id = m.mold_id
    WHERE ml.maintenance_start_timestamp IS NOT NULL
      AND ml.maintenance_end_timestamp IS NOT NULL
      AND {_COST_DATE_EXPR} BETWEEN %s AND %s
    ORDER BY hours DESC
    """


# ── 数据获取 ─────────────────────────────────────────────────────────
def get_cost_summary(start_date, end_date):
    try:
        row = execute_query(_build_cost_summary_query(),
                            params=(start_date, end_date), fetch_one=True)
    except sqlite3.Error as e:
        st.error(f"获取成本汇总失败: {e}")
        row = None
    if not row:
        return {'total_cost': 0.0, 'maintenance_count': 0, 'mold_count': 0}
    return {
        'total_cost': float(row.get('total_cost') or 0),
        'maintenance_count': int(row.get('maintenance_count') or 0),
        'mold_count': int(row.get('mold_count') or 0),
    }


def get_cost_trend_data(start_date, end_date):
    try:
        return execute_query(_build_cost_trend_query(),
                             params=(start_date, end_date), fetch_all=True) or []
    except sqlite3.Error as e:
        st.error(f"获取趋势数据失败: {e}")
        return []


def get_cost_composition(start_date, end_date):
    try:
        return execute_query(_build_cost_composition_query(),
                             params=(start_date, end_date), fetch_all=True) or []
    except sqlite3.Error as e:
        st.error(f"获取成本构成失败: {e}")
        return []


def get_mold_cost_details(start_date, end_date, repair_filter, sort_by, top_n):
    query = _build_mold_cost_details_query(repair_filter, sort_by)
    params = [start_date, end_date]
    if repair_filter is not None:
        params.append(repair_filter)
    params.append(int(top_n))
    try:
        return execute_query(query, params=tuple(params), fetch_all=True) or []
    except sqlite3.Error as e:
        st.error(f"获取模具成本明细失败: {e}")
        return []


def get_downtime_records(start_date, end_date):
    try:
        return execute_query(_build_downtime_query(),
                             params=(start_date, end_date), fetch_all=True) or []
    except sqlite3.Error as e:
        st.error(f"获取停机数据失败: {e}")
        return []


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


def _previous_period(start_date, end_date):
    """上一个等长周期，用于环比。"""
    length = (end_date - start_date)
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - length
    return prev_start, prev_end


def _pct_change(current, previous):
    """环比变化百分比；上期无数据返回 None（不显示）。"""
    if previous and previous > 0:
        return (current - previous) / previous * 100
    return None


# ── 页面 ─────────────────────────────────────────────────────────────
@require_permission('view_reports')
def show():
    """成本分析主页面"""
    inject_global_css()
    setup_sidebar("7_成本分析.py")
    page_header("💰", "成本分析仪表板", "维修保养费用 · 停机时长 · 真实数据")
    st.caption("📌 数据来源：维修保养记录中登记的费用与起止时间。请在维修管理中如实填写费用，分析才有意义。")

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
                value=(datetime.now().date() - timedelta(days=30), datetime.now().date()),
                key="custom_date_range"
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date = end_date = (date_range[0] if isinstance(date_range, (list, tuple)) else date_range)
        else:
            start_date, end_date = get_date_range(time_range)

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新数据", key="refresh_cost"):
            st.rerun()

    # 概览指标（真实聚合 + 与上一等长周期环比）
    summary = get_cost_summary(start_date, end_date)
    prev_start, prev_end = _previous_period(start_date, end_date)
    prev = get_cost_summary(prev_start, prev_end)

    st.markdown("### 📊 费用概览")
    c1, c2, c3, c4 = st.columns(4)

    cost_change = _pct_change(summary['total_cost'], prev['total_cost'])
    with c1:
        st.metric(
            "维修保养总费用",
            f"¥{summary['total_cost']:,.2f}",
            delta=(f"{cost_change:+.1f}% 环比" if cost_change is not None else None),
            delta_color="inverse"
        )
    with c2:
        cnt_change = _pct_change(summary['maintenance_count'], prev['maintenance_count'])
        st.metric(
            "维修保养次数",
            f"{summary['maintenance_count']} 次",
            delta=(f"{cnt_change:+.1f}% 环比" if cnt_change is not None else None),
            delta_color="inverse"
        )
    with c3:
        st.metric("涉及模具数", f"{summary['mold_count']} 个")
    with c4:
        avg = (summary['total_cost'] / summary['maintenance_count']
               if summary['maintenance_count'] else 0)
        st.metric("单次平均费用", f"¥{avg:,.2f}")

    tab1, tab2, tab3 = st.tabs(["📈 费用趋势", "🔧 模具费用明细", "⏱️ 停机时长"])

    with tab1:
        show_cost_trends(start_date, end_date)

    with tab2:
        show_mold_cost_details(start_date, end_date)

    with tab3:
        show_downtime_analysis(start_date, end_date)


def show_cost_trends(start_date, end_date):
    """费用趋势与构成"""
    st.subheader("📈 费用趋势")

    trend_data = get_cost_trend_data(start_date, end_date)
    if not trend_data:
        st.info("所选时间范围内暂无维修保养费用记录。")
        return

    df = pd.DataFrame(trend_data)
    fig = px.line(
        df, x='date', y='total_cost', markers=True,
        title='维修保养费用日趋势',
        labels={'date': '日期', 'total_cost': '费用 (元)'}
    )
    fig.update_layout(height=380, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    # 按维修类型的费用构成
    composition = get_cost_composition(start_date, end_date)
    if composition:
        col1, col2 = st.columns(2)
        comp_df = pd.DataFrame(composition)
        with col1:
            fig_pie = px.pie(
                comp_df, values='total_amount', names='cost_type',
                title='费用构成（按维修类型）'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            st.markdown("**各类型明细**")
            total = comp_df['total_amount'].sum()
            for _, row in comp_df.iterrows():
                pct = (row['total_amount'] / total * 100) if total > 0 else 0
                st.markdown(
                    f"- **{row['cost_type']}**：¥{row['total_amount']:,.2f}"
                    f"（{pct:.1f}% · {row['cnt']} 次）"
                )


def show_mold_cost_details(start_date, end_date):
    """模具费用明细（按模具聚合维修保养费用）"""
    st.subheader("🔧 模具费用明细")

    col1, col2, col3 = st.columns(3)
    with col1:
        type_filter = st.selectbox(
            "类型", ["全部", "仅维修", "仅保养"], key="cost_type_filter"
        )
    with col2:
        sort_by = st.selectbox("排序方式", list(_MOLD_COST_SORTS.keys()), key="cost_sort")
    with col3:
        top_n = st.number_input("显示前N个", min_value=5, max_value=50, value=10)

    repair_filter = {"全部": None, "仅维修": 1, "仅保养": 0}[type_filter]
    mold_costs = get_mold_cost_details(start_date, end_date, repair_filter, sort_by, top_n)

    if not mold_costs:
        st.info("所选条件下暂无费用记录。")
        return

    df = pd.DataFrame(mold_costs)

    fig = px.bar(
        df, x='total_cost', y='mold_name', orientation='h',
        title=f'模具维修保养费用排行（前{len(df)}名）',
        labels={'total_cost': '总费用 (元)', 'mold_name': '模具名称'}
    )
    fig.update_layout(height=300 + len(df) * 28)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 明细表")
    show_df = df.copy()
    show_df['总费用'] = show_df['total_cost'].apply(lambda x: f"¥{x:,.2f}")
    show_df['单次平均'] = show_df['avg_cost'].apply(lambda x: f"¥{x:,.2f}")
    st.dataframe(
        show_df[['mold_code', 'mold_name', '总费用', 'maintenance_count', '单次平均']],
        column_config={
            'mold_code': '模具编号',
            'mold_name': '模具名称',
            'maintenance_count': '维修保养次数',
        },
        hide_index=True,
        use_container_width=True
    )

    csv = show_df[['mold_code', 'mold_name', '总费用', 'maintenance_count', '单次平均']].to_csv(
        index=False, encoding='utf-8-sig')
    st.download_button(
        "📥 导出费用明细",
        csv,
        f"模具费用明细_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )


def show_downtime_analysis(start_date, end_date):
    """停机时长分析（按维修记录起止时间计算）"""
    st.subheader("⏱️ 停机时长分析")
    st.caption("停机时长按维修保养记录的起止时间计算；未填写结束时间的记录不计入。")

    records = get_downtime_records(start_date, end_date)
    if not records:
        st.info("所选时间范围内暂无可计算的停机记录（需同时填写开始与结束时间）。")
        return

    df = pd.DataFrame(records)
    df['hours'] = df['hours'].astype(float).clip(lower=0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("总停机时长", f"{df['hours'].sum():.1f} 小时")
    with c2:
        st.metric("停机次数", f"{len(df)} 次")
    with c3:
        st.metric("平均停机时长", f"{df['hours'].mean():.1f} 小时/次")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**停机时长 TOP 5（按模具）**")
        top_molds = (df.groupby(['mold_code', 'mold_name'])['hours']
                       .agg(['sum', 'count']).reset_index()
                       .sort_values('sum', ascending=False).head(5))
        for _, row in top_molds.iterrows():
            st.markdown(
                f"- **{row['mold_code']}** {row['mold_name']}："
                f"{row['sum']:.1f} 小时（{int(row['count'])} 次）"
            )

    with col2:
        daily = df.groupby('date')['hours'].sum().reset_index()
        fig = px.bar(
            daily, x='date', y='hours',
            title='停机时长日分布',
            labels={'date': '日期', 'hours': '停机时长 (小时)'}
        )
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)


show()
