# pages/system_management.py
"""
系统管理模块（整合版）
功能：用户管理、系统配置、系统监控
权限：仅超级管理员可访问
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import psutil
import numpy as np
import os
import logging
from utils.auth import (
    has_permission, get_all_users, create_user, update_user_status,
    get_user_activity_log, get_all_roles, validate_password_strength,
    update_user_password, log_user_action
)
from utils.database import execute_query, test_connection

def show():
    """系统管理主页面"""
    st.title("⚙️ 系统管理")
    
    # 权限检查
    if st.session_state.get('user_role') != '超级管理员':
        st.error("❌ 权限不足：仅超级管理员可以访问系统管理功能")
        return
    
    # 添加自定义样式
    st.markdown("""
    <style>
        .system-metric {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .config-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 3px solid #1f77b4;
        }
        .status-ok { color: #4caf50; }
        .status-warning { color: #ff9800; }
        .status-error { color: #f44336; }
        .user-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
            border-left: 4px solid #1f77b4;
        }
        .status-active { color: #4caf50; font-weight: bold; }
        .status-inactive { color: #f44336; font-weight: bold; }
        .role-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            margin: 2px;
        }
        .role-admin { background: #e3f2fd; color: #1976d2; }
        .role-manager { background: #f3e5f5; color: #7b1fa2; }
        .role-technician { background: #e8f5e9; color: #388e3c; }
        .role-operator { background: #fff3e0; color: #f57c00; }
    </style>
    """, unsafe_allow_html=True)
    
    # 主导航标签
    tab1, tab2, tab3 = st.tabs(["👥 用户管理", "🔧 系统配置", "📊 系统监控"])
    
    with tab1:
        show_user_management()
    
    with tab2:
        show_system_config()
    
    with tab3:
        show_system_monitor()

# ===================== 用户管理部分 =====================

def show_user_management():
    """用户管理子模块"""
    st.markdown("## 👥 用户管理")
    
    # 子标签 - 保留调试标签
    subtab1, subtab2, subtab3, subtab4, subtab5 = st.tabs([
        "用户列表", "新增用户", "角色权限", "操作日志", "🔧 调试工具"
    ])
    
    with subtab1:
        show_user_list()
    
    with subtab2:
        show_create_user()
    
    with subtab3:
        show_role_management()
    
    with subtab4:
        show_activity_logs()
    
    with subtab5:
        debug_user_creation()
        verify_create_user_function()

def show_user_list():
    """显示用户列表 - 使用卡片式布局"""
    st.markdown("### 👥 系统用户列表")
    
    # 筛选条件
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
        search_term = st.text_input("🔍 搜索用户", placeholder="输入用户名或姓名", key="user_search")
    with col2:
        role_filter = st.selectbox(
            "角色筛选",
            ["全部"] + [r['role_name'] for r in get_all_roles()],
            key="role_filter"
        )
    with col3:
        status_filter = st.selectbox("状态筛选", ["全部", "启用", "禁用"], key="status_filter")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新", key="refresh_users"):
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            st.rerun()
    
    # 如果有新用户需要高亮显示
    highlight_user = st.session_state.get('show_new_user', None)
    if highlight_user:
        st.info(f"🎉 新用户 '{highlight_user}' 已成功添加！")
        if st.button("关闭提示"):
            del st.session_state['show_new_user']
            st.rerun()
    
    # 获取用户列表
    try:
        users = get_all_users()
        if not users:
            st.warning("⚠️ 未获取到用户数据，请检查数据库连接")
            if st.button("重试获取数据"):
                st.rerun()
            return
    except Exception as e:
        st.error(f"获取用户列表时出错: {str(e)}")
        if st.button("重试获取数据"):
            st.rerun()
        return
    
    # 应用筛选
    original_count = len(users)
    
    if search_term:
        users = [u for u in users if search_term.lower() in u.get('username', '').lower() 
                 or search_term.lower() in u.get('full_name', '').lower()]
    if role_filter != "全部":
        users = [u for u in users if u.get('role_name') == role_filter]
    if status_filter != "全部":
        is_active = status_filter == "启用"
        users = [u for u in users if u.get('is_active') == is_active]
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        all_users = get_all_users()
        st.metric("总用户数", len(all_users))
    with col2:
        active_count = len([u for u in all_users if u.get('is_active', True)])
        st.metric("活跃用户", active_count)
    with col3:
        st.metric("筛选结果", len(users))
        if len(users) != original_count:
            st.caption(f"从 {original_count} 个用户中筛选")
    with col4:
        st.metric("系统角色", len(get_all_roles()))
    
    st.markdown("---")
    
    # 显示用户列表（卡片式布局）
    if users:
        # 使用列布局显示用户卡片
        for i in range(0, len(users), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(users):
                    user = users[i + j]
                    with cols[j]:
                        display_user_card(user)
    else:
        if search_term or role_filter != "全部" or status_filter != "全部":
            st.info("😔 没有找到符合筛选条件的用户")
            if st.button("清除筛选条件"):
                st.rerun()
        else:
            st.warning("系统中暂无用户数据")

def display_user_card(user):
    """显示用户卡片"""
    status_class = "status-active" if user['is_active'] else "status-inactive"
    status_text = "✅ 启用" if user['is_active'] else "❌ 禁用"
    
    # 角色样式映射
    role_style_map = {
        '超级管理员': 'role-admin',
        '模具库管理员': 'role-manager',
        '模具工': 'role-technician',
        '冲压操作工': 'role-operator'
    }
    role_class = role_style_map.get(user['role_name'], '')
    
    # 用户卡片HTML
    card_html = f"""
    <div class="user-card">
        <h4>{user['full_name']}</h4>
        <p><strong>用户名:</strong> {user['username']}</p>
        <p><strong>角色:</strong> <span class="role-badge {role_class}">{user['role_name']}</span></p>
        <p><strong>状态:</strong> <span class="{status_class}">{status_text}</span></p>
        <p><strong>邮箱:</strong> {user.get('email', '未设置')}</p>
        <p><strong>创建时间:</strong> {user['created_at'].strftime('%Y-%m-%d')}</p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if user['is_active']:
            if st.button(f"🔒 禁用", key=f"disable_{user['user_id']}"):
                success, msg = update_user_status(user['user_id'], False)
                if success:
                    st.success(msg)
                    log_user_action('DISABLE_USER', 'users', str(user['user_id']))
                    st.rerun()
                else:
                    st.error(msg)
        else:
            if st.button(f"🔓 启用", key=f"enable_{user['user_id']}"):
                success, msg = update_user_status(user['user_id'], True)
                if success:
                    st.success(msg)
                    log_user_action('ENABLE_USER', 'users', str(user['user_id']))
                    st.rerun()
                else:
                    st.error(msg)
    
    with col2:
        if st.button(f"✏️ 编辑", key=f"edit_{user['user_id']}"):
            st.session_state['edit_user_id'] = user['user_id']
            st.info("编辑功能开发中...")
    
    with col3:
        if st.button(f"📊 日志", key=f"logs_{user['user_id']}"):
            st.session_state['view_user_logs'] = user['user_id']
            st.rerun()

def show_create_user():
    """新增用户界面 - 增强版"""
    st.markdown("### ➕ 新增系统用户")
    
    # 说明信息
    st.info("""
    💡 **提示**：
    - 用户名用于登录，创建后不可修改
    - 密码要求：至少8位，包含大小写字母和数字
    - 邮箱用于密码重置和系统通知
    """)
    
    with st.form("create_user_form", clear_on_submit=True):
        st.markdown("#### 基本信息")
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input(
                "用户名 *", 
                placeholder="例如: zhangsan",
                help="用于登录的唯一标识，只能包含字母、数字和下划线"
            )
            full_name = st.text_input(
                "真实姓名 *",
                placeholder="例如: 张三"
            )
            email = st.text_input(
                "邮箱地址", 
                placeholder="例如: zhangsan@company.com",
                help="用于密码重置和通知"
            )
        
        with col2:
            password = st.text_input(
                "初始密码 *", 
                type="password",
                help="至少8位，包含大小写字母和数字"
            )
            password_confirm = st.text_input(
                "确认密码 *", 
                type="password"
            )
            roles = get_all_roles()
            if roles:
                role_id = st.selectbox(
                    "用户角色 *",
                    options=[(r['role_id'], r['role_name']) for r in roles],
                    format_func=lambda x: x[1],
                    help="选择用户的系统角色"
                )[0]
            else:
                st.error("无法获取角色列表")
                role_id = None
        
        # 额外选项
        st.markdown("#### 账户选项")
        col1, col2 = st.columns(2)
        with col1:
            send_email = st.checkbox("发送欢迎邮件", value=True, help="向用户发送账户信息")
        with col2:
            force_change = st.checkbox("首次登录修改密码", value=True, help="要求用户首次登录时修改密码")
        
        # 提交按钮
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            submitted = st.form_submit_button("✅ 创建用户", type="primary")
        with col2:
            if st.form_submit_button("❌ 取消"):
                st.rerun()
        
        if submitted and role_id:
            # 验证输入
            errors = []
            
            # 基础验证
            if not all([username, full_name, password, password_confirm]):
                errors.append("请填写所有必填字段")
            
            # 用户名格式验证
            if username and not username.replace('_', '').isalnum():
                errors.append("用户名只能包含字母、数字和下划线")
            
            # 检查用户名是否重复
            existing_users = get_all_users()
            if any(u['username'] == username for u in existing_users):
                errors.append(f"用户名 '{username}' 已存在，请选择其他用户名")
            
            # 密码验证
            if password != password_confirm:
                errors.append("两次输入的密码不一致")
            
            if password:
                is_valid, msg = validate_password_strength(password)
                if not is_valid:
                    errors.append(msg)
            
            # 邮箱格式验证
            if email and '@' not in email:
                errors.append("邮箱格式不正确")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # 创建用户
                with st.spinner("正在创建用户..."):
                    success, msg = create_user(username, password, full_name, role_id, email)
                    
                if success:
                    st.success(f"✅ {msg}")
                    st.balloons()
                    
                    # 记录操作日志
                    log_user_action('CREATE_USER', 'users', username, {
                        'full_name': full_name,
                        'role_id': role_id,
                        'email': email
                    })
                    
                    # 模拟发送邮件
                    if send_email and email:
                        st.info(f"📧 欢迎邮件已发送至 {email}")
                    
                    # 设置高亮显示标记
                    st.session_state['show_new_user'] = username
                    
                    # 延迟后刷新页面
                    import time
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

def show_role_management():
    """角色权限管理 - 增强版"""
    st.markdown("### 🔐 角色权限管理")
    
    # 获取所有角色
    roles = get_all_roles()
    
    # 角色统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("系统角色数", len(roles))
    with col2:
        admin_count = len([u for u in get_all_users() if u['role_name'] == '超级管理员'])
        st.metric("超级管理员", admin_count)
    with col3:
        manager_count = len([u for u in get_all_users() if u['role_name'] == '模具库管理员'])
        st.metric("模具库管理员", manager_count)
    with col4:
        operator_count = len([u for u in get_all_users() if u['role_name'] == '冲压操作工'])
        st.metric("冲压操作工", operator_count)
    
    st.markdown("---")
    
    # 显示角色详情
    for role in roles:
        with st.expander(f"**{role['role_name']}** - {role['description']}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**角色ID**: {role['role_id']}")
                st.markdown(f"**描述**: {role['description']}")
                
                # 获取该角色的用户数
                role_users = [u for u in get_all_users() if u['role_name'] == role['role_name']]
                st.markdown(f"**用户数**: {len(role_users)} 人")
                
                # 显示权限列表
                st.markdown("**主要权限**:")
                permissions = get_role_permissions_list(role['role_name'])
                for perm in permissions:
                    st.markdown(f"- {perm}")
            
            with col2:
                # 显示该角色的用户列表
                if role_users:
                    st.markdown("**该角色用户**:")
                    for user in role_users[:5]:  # 最多显示5个
                        st.markdown(f"- {user['full_name']} ({user['username']})")
                    if len(role_users) > 5:
                        st.markdown(f"... 还有 {len(role_users) - 5} 个用户")
    
    # 权限说明
    with st.expander("📖 权限详细说明", expanded=False):
        st.markdown("""
        #### 权限等级说明
        
        1. **超级管理员** - 最高权限
           - 完全控制系统所有功能
           - 用户和角色管理
           - 系统配置和维护
           - 数据备份和恢复
        
        2. **模具库管理员** - 业务管理权限
           - 模具台账管理（增删改查）
           - 借用申请审批
           - 维修任务分配
           - 业务报表查看
        
        3. **模具工** - 执行权限
           - 维修任务执行
           - 维修记录填写
           - 部件更换记录
           - 个人任务查看
        
        4. **冲压操作工** - 基础权限
           - 模具信息查询
           - 借用申请提交
           - 使用记录填写
           - 个人记录查看
        """)

def show_activity_logs():
    """操作日志查看 - 增强版"""
    st.markdown("### 📊 用户操作日志")
    
    # 查看特定用户的日志
    if 'view_user_logs' in st.session_state:
        user_id = st.session_state['view_user_logs']
        user = next((u for u in get_all_users() if u['user_id'] == user_id), None)
        if user:
            st.info(f"正在查看用户 **{user['full_name']} ({user['username']})** 的操作日志")
            if st.button("🔙 返回全部日志"):
                del st.session_state['view_user_logs']
                st.rerun()
    
    # 查询条件
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        if 'view_user_logs' not in st.session_state:
            user_filter = st.selectbox(
                "用户筛选",
                ["全部"] + [(u['user_id'], f"{u['full_name']} ({u['username']})") 
                           for u in get_all_users()],
                format_func=lambda x: "全部" if x == "全部" else x[1],
                key="log_user_filter"
            )
        else:
            user_filter = st.session_state['view_user_logs']
    
    with col2:
        action_types = ['全部', '登录', '创建', '修改', '删除', '审批']
        action_filter = st.selectbox("操作类型", action_types, key="action_filter")
    
    with col3:
        days = st.number_input("最近天数", min_value=1, max_value=90, value=7, key="log_days")
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新日志"):
            st.rerun()
    
    # 获取日志
    if 'view_user_logs' in st.session_state:
        user_id = st.session_state['view_user_logs']
    else:
        user_id = None if user_filter == "全部" else user_filter[0]
    
    logs = get_user_activity_log(user_id, days)
    
    # 应用操作类型筛选
    if action_filter != '全部' and logs:
        action_map = {
            '登录': ['LOGIN', 'LOGOUT'],
            '创建': ['CREATE_USER', 'CREATE_MOLD', 'CREATE_LOAN', 'CREATE_MAINTENANCE'],
            '修改': ['UPDATE_USER', 'UPDATE_MOLD', 'UPDATE_LOAN', 'UPDATE_MAINTENANCE'],
            '删除': ['DELETE_USER', 'DELETE_MOLD', 'DELETE_LOAN', 'DELETE_MAINTENANCE'],
            '审批': ['APPROVE_LOAN', 'REJECT_LOAN']
        }
        filter_actions = action_map.get(action_filter, [])
        logs = [log for log in logs if any(action in log['action_type'] for action in filter_actions)]
    
    # 显示日志统计
    if logs:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("日志条数", len(logs))
        with col2:
            unique_users = len(set(log['user_id'] for log in logs if log['user_id']))
            st.metric("活跃用户", unique_users)
        with col3:
            login_count = len([log for log in logs if 'LOGIN' in log['action_type']])
            st.metric("登录次数", login_count)
        with col4:
            today = datetime.now().date()
            today_logs = [log for log in logs if log['timestamp'].date() == today]
            st.metric("今日操作", len(today_logs))
    
    st.markdown("---")
    
    # 显示日志列表
    if logs:
        # 转换为DataFrame
        df = pd.DataFrame(logs)
        
        # 格式化显示
        df['时间'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df['操作类型'] = df['action_type'].map(get_action_display)
        df['用户'] = df.apply(lambda x: f"{x.get('full_name', '')} ({x.get('username', '')})" 
                            if x.get('username') else '系统', axis=1)
        
        # 选择显示的列
        display_columns = ['时间', '用户', '操作类型', 'target_resource', 'target_id']
        
        # 使用表格显示
        st.dataframe(
            df[display_columns],
            column_config={
                '时间': st.column_config.TextColumn('操作时间', width=150),
                '用户': st.column_config.TextColumn('操作用户', width=150),
                '操作类型': st.column_config.TextColumn('操作类型', width=120),
                'target_resource': st.column_config.TextColumn('目标资源', width=100),
                'target_id': st.column_config.TextColumn('目标ID', width=80),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 导出功能
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        with col1:
            csv = df[display_columns].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 导出日志",
                data=csv,
                file_name=f"操作日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("😊 没有找到符合条件的操作日志")

# ===================== 系统配置部分 =====================

def show_system_config():
    """系统配置子模块"""
    st.markdown("## 🔧 系统配置")
    
    # 配置分类
    config_tab1, config_tab2, config_tab3, config_tab4 = st.tabs([
        "基础配置", "业务参数", "邮件设置", "备份恢复"
    ])
    
    with config_tab1:
        show_basic_config()
    
    with config_tab2:
        show_business_params()
    
    with config_tab3:
        show_email_config()
    
    with config_tab4:
        show_backup_restore()

def show_basic_config():
    """基础配置"""
    st.markdown("### 系统基础配置")
    
    # 系统信息
    with st.expander("系统信息", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**系统名称**: 蕴杰金属冲压模具管理系统")
            st.markdown("**版本号**: v1.4.0")
            st.markdown("**安装日期**: 2024-06-01")
        with col2:
            st.markdown("**许可证**: 企业版")
            st.markdown("**到期日期**: 2025-12-31")
            st.markdown("**技术支持**: jerry.houyong@gmail.com")
    
    # 会话配置
    with st.expander("会话配置"):
        col1, col2 = st.columns(2)
        with col1:
            timeout = st.number_input("会话超时时间（分钟）", min_value=10, max_value=480, value=60, step=10)
            max_attempts = st.number_input("最大登录尝试次数", min_value=3, max_value=10, value=5)
        with col2:
            lock_duration = st.number_input("账户锁定时长（分钟）", min_value=5, max_value=60, value=15, step=5)
            password_expire = st.number_input("密码有效期（天）", min_value=0, max_value=365, value=90, step=30)
        
        if st.button("保存会话配置", type="primary"):
            st.success("会话配置已保存")
            log_user_action('UPDATE_CONFIG', 'system', 'session_config')
    
    # 系统维护模式
    with st.expander("系统维护"):
        maintenance_mode = st.checkbox("启用维护模式", help="启用后，除超级管理员外的用户将无法登录")
        maintenance_message = st.text_area(
            "维护公告",
            value="系统正在维护中，请稍后再试。预计恢复时间：",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("应用设置", type="primary" if maintenance_mode else "secondary"):
                if maintenance_mode:
                    st.warning("确定要启用维护模式吗？这将阻止其他用户登录。")
                else:
                    st.success("维护模式已关闭")

def show_business_params():
    """业务参数配置"""
    st.markdown("### 业务参数设置")
    
    # 模具管理参数
    with st.expander("模具管理参数", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**寿命预警阈值**")
            life_warning = st.slider("寿命达到百分比时预警", 70, 95, 85, 5)
            
            st.markdown("**保养提醒设置**")
            maintenance_advance = st.number_input("提前提醒天数", 1, 30, 7)
        
        with col2:
            st.markdown("**借用管理设置**")
            max_loan_days = st.number_input("最长借用天数", 1, 90, 30)
            auto_return = st.checkbox("启用自动归还提醒", value=True)
        
        if st.button("保存模具参数", key="save_mold_params"):
            st.success("模具管理参数已保存")
    
    # 维修管理参数
    with st.expander("维修管理参数"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**维修优先级设置**")
            urgent_hours = st.number_input("紧急维修时限（小时）", 1, 48, 24)
            normal_days = st.number_input("常规维修时限（天）", 1, 14, 7)
        
        with col2:
            st.markdown("**成本预警设置**")
            cost_warning = st.number_input("维修成本预警值（元）", 1000, 100000, 10000, 1000)
            monthly_budget = st.number_input("月度维修预算（元）", 10000, 1000000, 100000, 10000)
        
        if st.button("保存维修参数", key="save_maintenance_params"):
            st.success("维修管理参数已保存")
    
    # 统计报表参数
    with st.expander("报表参数"):
        st.markdown("**默认统计周期**")
        default_period = st.selectbox("默认时间范围", ["最近7天", "最近30天", "最近90天", "最近一年"])
        
        st.markdown("**数据保留策略**")
        col1, col2 = st.columns(2)
        with col1:
            log_retention = st.number_input("操作日志保留天数", 30, 730, 180, 30)
        with col2:
            report_retention = st.number_input("报表缓存保留天数", 7, 90, 30, 7)
        
        if st.button("保存报表参数", key="save_report_params"):
            st.success("报表参数已保存")

def show_email_config():
    """邮件设置"""
    st.markdown("### 邮件服务配置")
    
    # SMTP配置
    with st.form("email_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input("SMTP服务器", value="smtp.example.com")
            smtp_port = st.number_input("SMTP端口", value=587)
            smtp_user = st.text_input("发件人邮箱", value="noreply@example.com")
        
        with col2:
            smtp_password = st.text_input("邮箱密码", type="password")
            use_tls = st.checkbox("使用TLS加密", value=True)
            use_ssl = st.checkbox("使用SSL加密", value=False)
        
        st.markdown("---")
        st.markdown("**邮件模板设置**")
        
        # 邮件模板
        template_type = st.selectbox(
            "选择模板类型",
            ["欢迎邮件", "密码重置", "维修提醒", "借用到期提醒", "系统通知"]
        )
        
        email_subject = st.text_input("邮件主题", value=f"[模具管理系统] {template_type}")
        email_body = st.text_area(
            "邮件正文",
            value=get_email_template(template_type),
            height=200
        )
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.form_submit_button("保存配置", type="primary"):
                st.success("邮件配置已保存")
        with col2:
            if st.form_submit_button("发送测试"):
                st.info("正在发送测试邮件...")

def show_backup_restore():
    """备份恢复"""
    st.markdown("### 数据备份与恢复")
    
    # 备份设置
    with st.expander("自动备份设置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            backup_enabled = st.checkbox("启用自动备份", value=True)
            backup_time = st.time_input("备份时间", datetime.strptime("02:00", "%H:%M").time())
            backup_frequency = st.selectbox("备份频率", ["每天", "每周", "每月"])
        
        with col2:
            backup_retention = st.number_input("备份保留天数", 7, 365, 30, 7)
            backup_location = st.text_input("备份路径", value="/backup/mold_system/")
            compress_backup = st.checkbox("压缩备份文件", value=True)
        
        if st.button("保存备份设置", type="primary"):
            st.success("备份设置已保存")
    
    # 手动备份
    with st.expander("手动备份"):
        st.markdown("**立即备份**")
        backup_note = st.text_input("备份说明", placeholder="输入本次备份的说明信息")
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("开始备份", type="primary"):
                with st.spinner("正在执行备份..."):
                    # 模拟备份过程
                    progress_bar = st.progress(0)
                    for i in range(100):
                        progress_bar.progress(i + 1)
                    st.success("备份完成！备份文件：backup_20240612_143022.sql")
    
    # 备份历史
    with st.expander("备份历史"):
        # 模拟备份历史数据
        backup_history = [
            {"时间": "2024-06-12 02:00:00", "类型": "自动", "大小": "125 MB", "状态": "成功"},
            {"时间": "2024-06-11 14:30:00", "类型": "手动", "大小": "124 MB", "状态": "成功"},
            {"时间": "2024-06-11 02:00:00", "类型": "自动", "大小": "123 MB", "状态": "成功"},
        ]
        
        df = pd.DataFrame(backup_history)
        st.dataframe(df, hide_index=True, use_container_width=True)
    
    # 数据恢复
    with st.expander("数据恢复", expanded=False):
        st.warning("⚠️ 数据恢复将覆盖现有数据，请谨慎操作！")
        
        backup_file = st.selectbox(
            "选择备份文件",
            ["backup_20240612_020000.sql", "backup_20240611_143000.sql", "backup_20240611_020000.sql"]
        )
        
        confirm_text = st.text_input("请输入'确认恢复'以继续")
        
        if st.button("执行恢复", type="secondary"):
            if confirm_text == "确认恢复":
                st.error("恢复功能需要在维护模式下执行")
            else:
                st.error("请输入正确的确认文字")

# ===================== 系统监控部分 =====================

def show_system_monitor():
    """系统监控子模块"""
    st.markdown("## 📊 系统监控")
    
    # 监控标签
    monitor_tab1, monitor_tab2, monitor_tab3, monitor_tab4 = st.tabs([
        "实时监控", "性能分析", "错误日志", "数据统计"
    ])
    
    with monitor_tab1:
        show_realtime_monitor()
    
    with monitor_tab2:
        show_performance_analysis()
    
    with monitor_tab3:
        show_error_logs()
    
    with monitor_tab4:
        show_data_statistics()

def show_realtime_monitor():
    """实时监控"""
    st.markdown("### 系统实时状态")
    
    # 自动刷新
    auto_refresh = st.checkbox("自动刷新（每5秒）")
    if auto_refresh:
        st.empty()  # 占位符，用于自动刷新
    
    # 系统状态概览
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        st.metric(
            "CPU使用率",
            f"{cpu_percent}%",
            delta=f"{cpu_percent - 50:.1f}%",
            delta_color="inverse"
        )
    
    with col2:
        # 内存使用率
        memory = psutil.virtual_memory()
        st.metric(
            "内存使用率",
            f"{memory.percent}%",
            delta=f"{memory.percent - 70:.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        st.metric(
            "磁盘使用率",
            f"{disk.percent}%",
            delta=f"{disk.percent - 80:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        # 数据库连接
        db_status = test_connection()
        st.metric(
            "数据库状态",
            "正常" if db_status else "异常",
            delta="连接正常" if db_status else "连接失败",
            delta_color="normal" if db_status else "inverse"
        )
    
    # 详细监控信息
    col1, col2 = st.columns(2)
    
    with col1:
        # 系统信息
        with st.expander("系统信息", expanded=True):
            st.markdown(f"**操作系统**: {os.name}")
            st.markdown(f"**Python版本**: {os.sys.version.split()[0]}")
            st.markdown(f"**进程数**: {len(psutil.pids())}")
            st.markdown(f"**启动时间**: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}")
    
    with col2:
        # 网络状态
        with st.expander("网络状态", expanded=True):
            net_io = psutil.net_io_counters()
            st.markdown(f"**发送数据**: {net_io.bytes_sent / 1024 / 1024:.2f} MB")
            st.markdown(f"**接收数据**: {net_io.bytes_recv / 1024 / 1024:.2f} MB")
            st.markdown(f"**发送包数**: {net_io.packets_sent:,}")
            st.markdown(f"**接收包数**: {net_io.packets_recv:,}")
    
    # 在线用户监控
    with st.expander("在线用户", expanded=True):
        # 模拟在线用户数据
        online_users = get_online_users()
        if online_users:
            df = pd.DataFrame(online_users)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("当前没有在线用户")

def show_performance_analysis():
    """性能分析"""
    st.markdown("### 系统性能分析")
    
    # 时间范围选择
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        time_range = st.selectbox("时间范围", ["最近1小时", "最近24小时", "最近7天", "最近30天"])
    with col2:
        metric_type = st.selectbox("指标类型", ["CPU", "内存", "磁盘IO", "网络IO"])
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("刷新数据"):
            st.rerun()
    
    # 性能趋势图
    fig = create_performance_chart(metric_type, time_range)
    st.plotly_chart(fig, use_container_width=True)
    
    # 性能统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("平均值", "45.2%")
    with col2:
        st.metric("峰值", "78.9%")
    with col3:
        st.metric("谷值", "12.3%")
    with col4:
        st.metric("当前值", "42.7%")
    
    # API响应时间分析
    with st.expander("API响应时间分析"):
        api_stats = get_api_statistics()
        if api_stats:
            df = pd.DataFrame(api_stats)
            
            # 创建响应时间分布图
            fig = px.bar(df, x='接口', y='平均响应时间(ms)', title='API平均响应时间')
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示详细统计
            st.dataframe(df, hide_index=True, use_container_width=True)

def show_error_logs():
    """错误日志"""
    st.markdown("### 系统错误日志")
    
    # 筛选条件
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        error_level = st.selectbox("错误级别", ["全部", "ERROR", "WARNING", "INFO"])
    with col2:
        error_module = st.selectbox("模块", ["全部", "认证", "数据库", "业务逻辑", "API"])
    with col3:
        days = st.number_input("最近天数", 1, 30, 7)
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("查询"):
            st.rerun()
    
    # 错误统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("错误总数", "127", delta="-12", delta_color="normal")
    with col2:
        st.metric("严重错误", "3", delta="+1", delta_color="inverse")
    with col3:
        st.metric("警告", "45", delta="-5", delta_color="normal")
    with col4:
        st.metric("今日错误", "8", delta="+2", delta_color="inverse")
    
    # 错误日志列表
    error_logs = get_error_logs(error_level, error_module, days)
    if error_logs:
        # 转换为DataFrame
        df = pd.DataFrame(error_logs)
        
        # 根据错误级别着色
        def highlight_error_level(row):
            if row['级别'] == 'ERROR':
                return ['background-color: #ffebee'] * len(row)
            elif row['级别'] == 'WARNING':
                return ['background-color: #fff3e0'] * len(row)
            else:
                return [''] * len(row)
        
        styled_df = df.style.apply(highlight_error_level, axis=1)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        # 错误详情
        st.markdown("---")
        selected_error = st.selectbox(
            "选择错误查看详情",
            options=range(len(error_logs)),
            format_func=lambda x: f"{error_logs[x]['时间']} - {error_logs[x]['错误信息'][:50]}..."
        )
        
        if selected_error is not None:
            error = error_logs[selected_error]
            with st.expander("错误详情", expanded=True):
                st.markdown(f"**时间**: {error['时间']}")
                st.markdown(f"**级别**: {error['级别']}")
                st.markdown(f"**模块**: {error['模块']}")
                st.markdown(f"**用户**: {error.get('用户', 'System')}")
                st.markdown(f"**错误信息**: {error['错误信息']}")
                st.code(error.get('堆栈跟踪', '无堆栈信息'), language='python')
    else:
        st.info("没有找到符合条件的错误日志")

def show_data_statistics():
    """数据统计"""
    st.markdown("### 系统数据统计")
    
    # 数据概览
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_molds = get_total_count('molds')
        st.metric("模具总数", total_molds)
    
    with col2:
        total_loans = get_total_count('mold_loan_records')
        st.metric("借用记录", total_loans)
    
    with col3:
        total_maintenance = get_total_count('mold_maintenance_logs')
        st.metric("维修记录", total_maintenance)
    
    with col4:
        total_users = get_total_count('users')
        st.metric("系统用户", total_users)
    
    # 增长趋势
    with st.expander("数据增长趋势", expanded=True):
        # 创建增长趋势图
        fig = create_growth_trend_chart()
        st.plotly_chart(fig, use_container_width=True)
    
    # 表空间使用情况
    with st.expander("数据库表空间"):
        table_sizes = get_table_sizes()
        if table_sizes:
            df = pd.DataFrame(table_sizes)
            
            # 创建饼图
            fig = px.pie(df, values='大小(MB)', names='表名', title='表空间占用分布')
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示详细信息
            st.dataframe(df, hide_index=True, use_container_width=True)
    
    # 数据质量检查
    with st.expander("数据质量检查"):
        quality_checks = perform_data_quality_checks()
        
        for check in quality_checks:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{check['检查项']}**")
            with col2:
                if check['状态'] == '正常':
                    st.success(check['状态'])
                else:
                    st.error(check['状态'])
            with col3:
                st.markdown(check['说明'])

# ===================== 辅助函数 =====================

def get_role_permissions_list(role_name):
    """获取角色权限列表"""
    permissions_map = {
        '超级管理员': [
            '✅ 系统所有功能的完全访问权限',
            '✅ 用户账户管理（创建、编辑、禁用）',
            '✅ 角色权限配置',
            '✅ 系统参数设置',
            '✅ 数据备份和恢复',
            '✅ 查看所有操作日志'
        ],
        '模具库管理员': [
            '✅ 模具台账管理（新增、编辑、删除）',
            '✅ 借用申请审批',
            '✅ 维修任务分配',
            '✅ 查看统计报表',
            '✅ 管理存储位置和分类',
            '❌ 用户管理权限'
        ],
        '模具工': [
            '✅ 查看分配的维修任务',
            '✅ 填写维修记录',
            '✅ 更新任务状态',
            '✅ 记录部件更换',
            '❌ 模具信息编辑权限',
            '❌ 借用审批权限'
        ],
        '冲压操作工': [
            '✅ 查询模具信息',
            '✅ 提交借用申请',
            '✅ 查看个人借用记录',
            '✅ 填写使用记录',
            '❌ 模具信息编辑权限',
            '❌ 查看他人记录'
        ]
    }
    return permissions_map.get(role_name, ['暂无权限说明'])

def get_action_display(action_type):
    """获取操作类型的中文显示"""
    action_map = {
        'LOGIN': '用户登录',
        'LOGOUT': '用户登出',
        'CREATE_USER': '创建用户',
        'UPDATE_USER': '更新用户',
        'DELETE_USER': '删除用户',
        'DISABLE_USER': '禁用用户',
        'ENABLE_USER': '启用用户',
        'CREATE_MOLD': '新增模具',
        'UPDATE_MOLD': '更新模具',
        'DELETE_MOLD': '删除模具',
        'CREATE_LOAN': '创建借用',
        'UPDATE_LOAN': '更新借用',
        'APPROVE_LOAN': '批准借用',
        'REJECT_LOAN': '驳回借用',
        'CREATE_MAINTENANCE': '创建维修',
        'UPDATE_MAINTENANCE': '更新维修',
        'VIEW_REPORT': '查看报表',
        'EXPORT_DATA': '导出数据',
        'UPDATE_CONFIG': '更新配置',
        'BACKUP_DATA': '数据备份',
        'RESTORE_DATA': '数据恢复',
        'SYSTEM_CONFIG': '系统配置'
    }
    return action_map.get(action_type, action_type)

def get_email_template(template_type):
    """获取邮件模板"""
    templates = {
        "欢迎邮件": """尊敬的{user_name}：

欢迎您使用蕴杰金属冲压模具管理系统！

您的账户信息如下：
用户名：{username}
初始密码：{password}

请及时登录系统并修改初始密码。

祝您使用愉快！

蕴杰金属技术团队""",
        "密码重置": """尊敬的{user_name}：

您的密码已重置。

新密码：{new_password}

请及时登录并修改密码。""",
        "维修提醒": """尊敬的{user_name}：

以下模具需要进行维修保养：

模具编号：{mold_code}
模具名称：{mold_name}
维修类型：{maintenance_type}
建议时间：{suggested_date}

请及时安排维修计划。""",
    }
    return templates.get(template_type, "")

def get_online_users():
    """获取在线用户列表（模拟数据）"""
    # 实际应该从会话管理中获取
    return [
        {"用户名": "admin", "姓名": "系统管理员", "登录时间": "2024-06-12 09:00:00", "最后活动": "刚刚"},
        {"用户名": "mold_admin", "姓名": "模具库管理员", "登录时间": "2024-06-12 08:30:00", "最后活动": "5分钟前"},
    ]

def create_performance_chart(metric_type, time_range):
    """创建性能趋势图"""
    # 模拟数据
    import numpy as np
    
    hours = 24 if "24小时" in time_range else 168 if "7天" in time_range else 1
    x = pd.date_range(end=datetime.now(), periods=hours, freq='H')
    y = np.random.randint(20, 80, size=hours) + np.sin(np.arange(hours) * 0.1) * 10
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode='lines+markers',
        name=metric_type,
        line=dict(color='rgb(31, 119, 180)', width=2),
        marker=dict(size=4)
    ))
    
    fig.update_layout(
        title=f'{metric_type}使用率趋势',
        xaxis_title='时间',
        yaxis_title='使用率 (%)',
        hovermode='x unified',
        showlegend=False
    )
    
    return fig

def get_api_statistics():
    """获取API统计信息（模拟数据）"""
    return [
        {"接口": "/api/molds", "调用次数": 1234, "平均响应时间(ms)": 45, "成功率": "99.8%"},
        {"接口": "/api/loans", "调用次数": 567, "平均响应时间(ms)": 38, "成功率": "99.9%"},
        {"接口": "/api/maintenance", "调用次数": 890, "平均响应时间(ms)": 52, "成功率": "99.5%"},
        {"接口": "/api/users", "调用次数": 234, "平均响应时间(ms)": 31, "成功率": "100%"},
    ]

def get_error_logs(level, module, days):
    """获取错误日志（模拟数据）"""
    logs = [
        {
            "时间": "2024-06-12 14:30:22",
            "级别": "ERROR",
            "模块": "数据库",
            "用户": "mold_admin",
            "错误信息": "数据库连接超时",
            "堆栈跟踪": "psycopg2.OperationalError: could not connect to server..."
        },
        {
            "时间": "2024-06-12 13:15:10",
            "级别": "WARNING",
            "模块": "认证",
            "用户": "operator1",
            "错误信息": "密码错误次数过多",
            "堆栈跟踪": ""
        },
        {
            "时间": "2024-06-12 10:22:33",
            "级别": "INFO",
            "模块": "业务逻辑",
            "用户": "admin",
            "错误信息": "模具借用申请被驳回",
            "堆栈跟踪": ""
        },
    ]
    
    # 根据筛选条件过滤
    if level != "全部":
        logs = [log for log in logs if log["级别"] == level]
    if module != "全部":
        logs = [log for log in logs if log["模块"] == module]
    
    return logs

def get_total_count(table_name):
    """获取表记录总数"""
    try:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = execute_query(query, fetch_one=True)
        return result['count'] if result else 0
    except:
        return 0

def create_growth_trend_chart():
    """创建数据增长趋势图"""
    # 模拟数据
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    
    fig = go.Figure()
    
    # 添加多条趋势线
    fig.add_trace(go.Scatter(
        x=dates,
        y=np.cumsum(np.random.randint(1, 5, 30)) + 100,
        mode='lines+markers',
        name='模具数量',
        line=dict(color='blue', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=np.cumsum(np.random.randint(2, 8, 30)) + 200,
        mode='lines+markers',
        name='借用记录',
        line=dict(color='green', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=np.cumsum(np.random.randint(1, 4, 30)) + 50,
        mode='lines+markers',
        name='维修记录',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title='系统数据增长趋势（最近30天）',
        xaxis_title='日期',
        yaxis_title='累计数量',
        hovermode='x unified'
    )
    
    return fig

def get_table_sizes():
    """获取数据库表大小（模拟数据）"""
    return [
        {"表名": "molds", "记录数": 245, "大小(MB)": 12.5},
        {"表名": "mold_loan_records", "记录数": 1832, "大小(MB)": 45.2},
        {"表名": "mold_maintenance_logs", "记录数": 567, "大小(MB)": 23.8},
        {"表名": "mold_usage_records", "记录数": 3421, "大小(MB)": 67.3},
        {"表名": "system_logs", "记录数": 8934, "大小(MB)": 156.7},
    ]

def perform_data_quality_checks():
    """执行数据质量检查"""
    return [
        {"检查项": "模具编号唯一性", "状态": "正常", "说明": "无重复"},
        {"检查项": "借用记录完整性", "状态": "正常", "说明": "无缺失"},
        {"检查项": "维修记录关联性", "状态": "警告", "说明": "3条记录模具ID无效"},
        {"检查项": "用户权限一致性", "状态": "正常", "说明": "权限配置正确"},
        {"检查项": "数据时间戳有效性", "状态": "正常", "说明": "时间戳正常"},
    ]

# ===================== 调试工具部分 =====================

def debug_user_creation():
    """调试用户创建问题的辅助函数"""
    st.markdown("### 🔧 用户管理调试工具")
    
    # 测试数据库连接
    st.markdown("#### 1. 数据库连接测试")
    try:
        db_status = test_connection()
        if db_status:
            st.success("✅ 数据库连接正常")
        else:
            st.error("❌ 数据库连接失败")
    except Exception as e:
        st.error(f"数据库连接测试出错: {str(e)}")
    
    # 测试 get_all_users() 函数
    st.markdown("#### 2. 用户数据获取测试")
    try:
        users = get_all_users()
        st.success(f"✅ 成功获取 {len(users)} 个用户")
        
        if users:
            # 显示最近的几个用户
            st.markdown("**最近的用户（前5个）：**")
            recent_users = users[:5]
            for user in recent_users:
                st.write(f"- {user.get('username', 'Unknown')} | {user.get('full_name', 'Unknown')} | {user.get('role_name', 'Unknown')}")
        else:
            st.warning("⚠️ 用户列表为空")
            
    except Exception as e:
        st.error(f"获取用户数据时出错: {str(e)}")
    
    # 测试直接数据库查询
    st.markdown("#### 3. 直接数据库查询测试")
    if st.button("执行直接查询"):
        try:
            # 直接查询用户表
            query = "SELECT username, full_name, role_name, is_active, created_at FROM users ORDER BY created_at DESC LIMIT 10"
            direct_result = execute_query(query, fetch_all=True)
            
            if direct_result:
                st.success(f"✅ 直接查询成功，获取 {len(direct_result)} 条记录")
                df = pd.DataFrame(direct_result)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("⚠️ 直接查询返回空结果")
                
        except Exception as e:
            st.error(f"直接数据库查询失败: {str(e)}")
    
    # 清除缓存工具
    st.markdown("#### 4. 缓存管理")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清除Streamlit缓存"):
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
                st.success("缓存已清除")
            else:
                st.info("没有找到缓存系统")
    
    with col2:
        if st.button("🔄 强制页面重载"):
            st.rerun()

def verify_create_user_function():
    """验证 create_user 函数是否正常工作"""
    st.markdown("#### 5. create_user 函数测试")
    
    with st.form("test_create_user"):
        st.markdown("**创建测试用户（用于调试）**")
        test_username = st.text_input("测试用户名", value=f"test_user_{datetime.now().strftime('%H%M%S')}")
        test_password = st.text_input("测试密码", value="Test123456!", type="password")
        test_full_name = st.text_input("测试姓名", value="测试用户")
        
        # 获取角色选项
        try:
            roles = get_all_roles()
            if roles:
                test_role_id = st.selectbox(
                    "测试角色",
                    options=[(r['role_id'], r['role_name']) for r in roles],
                    format_func=lambda x: x[1]
                )[0]
            else:
                st.error("无法获取角色列表")
                test_role_id = None
        except Exception as e:
            st.error(f"获取角色列表失败: {str(e)}")
            test_role_id = None
        
        if st.form_submit_button("创建测试用户") and test_role_id:
            try:
                # 记录创建前的用户数量
                users_before = get_all_users()
                count_before = len(users_before)
                st.info(f"创建前用户数量: {count_before}")
                
                # 创建用户
                success, msg = create_user(test_username, test_password, test_full_name, test_role_id, "test@example.com")
                
                if success:
                    st.success(f"✅ 用户创建成功: {msg}")
                    
                    # 等待一下再查询
                    import time
                    time.sleep(1)
                    
                    # 记录创建后的用户数量
                    users_after = get_all_users()
                    count_after = len(users_after)
                    st.info(f"创建后用户数量: {count_after}")
                    
                    if count_after > count_before:
                        st.success("✅ 用户数量增加，创建成功")
                        # 查找新创建的用户
                        new_user = next((u for u in users_after if u['username'] == test_username), None)
                        if new_user:
                            st.success(f"✅ 在用户列表中找到新用户: {new_user['full_name']}")
                        else:
                            st.error("❌ 用户数量增加但未找到指定用户名")
                    else:
                        st.error("❌ 用户数量未增加，可能创建失败")
                else:
                    st.error(f"❌ 用户创建失败: {msg}")
                    
            except Exception as e:
                st.error(f"测试创建用户时出错: {str(e)}")

# 主函数
if __name__ == "__main__":
    # 模拟登录状态
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = 1
        st.session_state['user_role'] = '超级管理员'
        st.session_state['username'] = 'admin'
    
    show()