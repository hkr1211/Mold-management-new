# app/utils/auth.py - 完整修复版

import streamlit as st
import bcrypt
import functools
import sqlite3
from utils.database import execute_query, check_table_exists
import logging
import json
import re
from datetime import datetime, timedelta

try:
    from config.settings import (
        LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS, PASSWORD_MIN_LENGTH
    )
except ImportError:
    LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS, PASSWORD_MIN_LENGTH = 5, 300, 8

# 日志：库模块只取 logger，全局配置交给入口 main.py
logger = logging.getLogger(__name__)

# 角色权限映射（保持硬编码，未来可移到DB）
ROLE_PERMISSIONS = {
    '超级管理员': ['*'],
    '模具库管理员': [
        'view_molds', 'manage_molds', 'approve_loans', 
        'view_reports', 'manage_schedule', 'manage_users'
    ],
    '模具工': [
        'view_molds', 'manage_maintenance', 'view_own_tasks'
    ],
    '冲压操作工': [
        'view_molds', 'create_loan', 'view_own_loans', 'view_schedule'
    ]
}

def check_password(username: str, password: str):
    """验证用户密码 - 全bcrypt版本"""
    
    # 查询用户
    simple_query = """
    SELECT 
        user_id, 
        password_hash, 
        full_name, 
        email,
        is_active,
        role_id
    FROM users
    WHERE username = %s AND is_active = true
    """
    
    try:
        logger.info(f"执行登录查询，用户名: {username}")
        user = execute_query(simple_query, params=(username,), fetch_one=True)
        logger.debug(f"查询结果: {user}")
        
        if not user:
            logger.warning(f"用户不存在或未激活: {username}")
            return None
            
        logger.info(f"用户存在，检查密码...")
        
        # 只用bcrypt验证
        password_check = bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))
        logger.debug(f"bcrypt密码验证结果: {password_check}")
        
        if password_check:
            # 获取角色名称，从DB查询
            role_name = None
            if user.get('role_id'):
                try:
                    role_query = "SELECT role_name FROM roles WHERE role_id = %s"
                    role_result = execute_query(role_query, params=(user['role_id'],), fetch_one=True)
                    if role_result:
                        role_name = role_result['role_name']
                except sqlite3.Error as e:
                    logger.error(f"获取角色失败: {e}")
                    return None  # 失败不登录
            
            if not role_name:
                logger.warning(f"用户 {username} 无有效角色")
                return None
            
            return {
                'user_id': user['user_id'],
                'username': username,
                'full_name': user.get('full_name', username),
                'email': user.get('email', ''),
                'role': role_name
            }
        else:
            logger.warning(f"密码验证失败: {username}")
            return None
            
    except sqlite3.Error as e:
        logger.error(f"登录查询错误: {e}")
        return None

def has_permission(permission: str) -> bool:
    """检查当前用户是否有指定权限"""
    if not st.session_state.get('logged_in'):
        return False
    
    user_role = st.session_state.get('user_role', '')
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    
    if '*' in permissions:
        return True
    
    return permission in permissions

_LOCK_TIME_FMT = '%Y-%m-%d %H:%M:%S'

def _get_lockout_record(username: str):
    """读取某用户名的失败计数/锁定记录。"""
    try:
        return execute_query(
            "SELECT attempts, locked_until FROM login_attempts WHERE username = %s",
            params=(username,), fetch_one=True
        )
    except sqlite3.Error as e:
        logger.error(f"读取登录锁定记录失败: {e}")
        return None

def _is_locked(record) -> bool:
    """根据记录判断账号是否仍在锁定时段内。"""
    if not record or not record.get('locked_until'):
        return False
    try:
        locked_until = datetime.strptime(record['locked_until'], _LOCK_TIME_FMT)
    except (ValueError, TypeError):
        return False
    return datetime.now() < locked_until

def _register_failed_attempt(username: str) -> None:
    """登录失败：服务端累加计数，达阈值则写入锁定截止时间。"""
    record = _get_lockout_record(username)
    attempts = (record['attempts'] if record else 0) + 1
    locked_until = None
    if attempts >= LOGIN_MAX_ATTEMPTS:
        locked_until = (datetime.now() + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)).strftime(_LOCK_TIME_FMT)
    now = datetime.now().strftime(_LOCK_TIME_FMT)
    try:
        execute_query(
            """
            INSERT INTO login_attempts (username, attempts, last_attempt, locked_until)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(username) DO UPDATE SET
                attempts     = excluded.attempts,
                last_attempt = excluded.last_attempt,
                locked_until = excluded.locked_until
            """,
            params=(username, attempts, now, locked_until), commit=True
        )
    except sqlite3.Error as e:
        logger.error(f"写入登录失败计数失败: {e}")

def _reset_attempts(username: str) -> None:
    """登录成功：清除该用户名的失败计数。"""
    try:
        execute_query(
            "DELETE FROM login_attempts WHERE username = %s",
            params=(username,), commit=True
        )
    except sqlite3.Error as e:
        logger.error(f"清除登录失败计数失败: {e}")

def login_user(username: str, password: str):
    """用户登录 - 服务端失败计数与锁定（基于 DB，清除会话无法绕过）"""
    # 服务端锁定检查
    if _is_locked(_get_lockout_record(username)):
        logger.warning(f"账号锁定中，拒绝登录: {username}")
        return None

    user_info = check_password(username, password)

    if user_info:
        logger.info(f"登录成功: {username}")
        # 重置失败计数
        _reset_attempts(username)
        # 设置会话
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user_info['user_id']
        st.session_state['username'] = user_info['username']
        st.session_state['full_name'] = user_info.get('full_name', user_info['username'])
        st.session_state['user_role'] = user_info['role']

        # 记录日志
        try:
            log_user_action('LOGIN', 'system', username)
        except Exception as e:
            logger.error(f"记录登录日志失败: {e}")

        return user_info
    else:
        _register_failed_attempt(username)
        logger.warning(f"登录失败: {username}")
        return None

def logout_user():
    """用户登出"""
    username = st.session_state.get('username', '')
    
    # 记录日志
    if username:
        try:
            log_user_action('LOGOUT', 'system', username)
        except Exception as e:
            logger.error(f"记录登出日志失败: {e}")

    # 清除会话
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def log_user_action(action_type: str, target_resource: str, 
                    target_id: str, details: dict = None):
    """记录用户操作日志"""
    user_id = st.session_state.get('user_id')
    if not user_id:
        return
    
    try:
        # 检查表存在
        if not check_table_exists('system_logs'):
            logger.warning("system_logs表不存在，跳过日志记录")
            return

        # 记录日志
        query = """
        INSERT INTO system_logs (user_id, action_type, target_resource,
                                 target_id, details, timestamp)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        
        details_json = json.dumps(details) if details else None
        execute_query(
            query,
            params=(user_id, action_type, target_resource, target_id, details_json),
            commit=True
        )
        logger.info(f"日志记录成功: {action_type}")
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")

def get_all_users(offset: int = 0, limit: int = 100):
    """获取所有用户列表，支持分页"""
    if not has_permission('manage_users'):
        logger.warning("用户没有manage_users权限")
        return []
    
    query = """
    SELECT 
        u.user_id, 
        u.username, 
        u.full_name, 
        u.email, 
        u.is_active, 
        r.role_name,
        u.created_at
    FROM users u
    LEFT JOIN roles r ON u.role_id = r.role_id
    ORDER BY u.created_at DESC
    LIMIT %s OFFSET %s
    """
    try:
        result = execute_query(query, params=(limit, offset), fetch_all=True)
        logger.info(f"获取用户列表成功，共 {len(result) if result else 0} 个用户")
        return result or []
    except sqlite3.Error as e:
        logger.error(f"获取用户列表失败: {e}")
        return []

def create_user(username: str, password: str, full_name: str, 
                role_name: str, email: str = None):
    """创建新用户"""
    # 检查用户名存在
    check_query = "SELECT user_id FROM users WHERE username = %s"
    existing = execute_query(check_query, params=(username,), fetch_one=True)
    
    if existing:
        return False, "用户名已存在"
    
    # 获取 role_id。兼容传入 role_name 或 role_id
    if isinstance(role_name, int) or (isinstance(role_name, str) and role_name.isdigit()):
        role_query = "SELECT role_id FROM roles WHERE role_id = %s"
        role_lookup_value = int(role_name)
    else:
        role_query = "SELECT role_id FROM roles WHERE role_name = %s"
        role_lookup_value = role_name

    role_result = execute_query(role_query, params=(role_lookup_value,), fetch_one=True)
    
    if not role_result:
        return False, f"角色 '{role_name}' 不存在"
    
    role_id = role_result['role_id']
    
    # 生成hash
    password_hash = bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
    
    insert_query = """
    INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
    """
    
    try:
        rowcount = execute_query(
            insert_query, 
            params=(username, password_hash, full_name, role_id, email), 
            commit=True
        )
        if rowcount > 0:
            logger.info(f"用户创建成功: {username}")
            return True, "用户创建成功"
        else:
            return False, "用户创建失败"
    except sqlite3.Error as e:
        logger.error(f"创建用户失败: {e}")
        return False, f"创建失败: {str(e)}"

def update_user_status(user_id: int, is_active: bool):
    """更新用户状态"""
    query = "UPDATE users SET is_active = %s, updated_at = NOW() WHERE user_id = %s"
    try:
        rowcount = execute_query(query, params=(is_active, user_id), commit=True)
        if rowcount > 0:
            status_text = "启用" if is_active else "禁用"
            return True, f"用户已{status_text}"
        else:
            return False, "用户不存在"
    except sqlite3.Error as e:
        logger.error(f"更新用户状态失败: {e}")
        return False, f"更新失败: {str(e)}"

def update_user(user_id: int, full_name: str, email: str = None, role_name=None):
    """更新用户基本信息（姓名/邮箱/角色）。用户名不可修改；启用状态与密码另有专用函数。

    role_name 可传角色名或 role_id；传 None/'' 时保持原角色不变。
    """
    full_name = (full_name or '').strip()
    if not full_name:
        return False, "姓名不能为空"
    email = email.strip() if (email and email.strip()) else None

    set_clauses = ["full_name = %s", "email = %s"]
    params = [full_name, email]

    # 解析并更新角色（可选）
    if role_name not in (None, ''):
        if isinstance(role_name, int) or (isinstance(role_name, str) and role_name.isdigit()):
            role_result = execute_query(
                "SELECT role_id FROM roles WHERE role_id = %s",
                params=(int(role_name),), fetch_one=True
            )
        else:
            role_result = execute_query(
                "SELECT role_id FROM roles WHERE role_name = %s",
                params=(role_name,), fetch_one=True
            )
        if not role_result:
            return False, f"角色 '{role_name}' 不存在"
        set_clauses.append("role_id = %s")
        params.append(role_result['role_id'])

    set_clauses.append("updated_at = NOW()")
    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = %s"
    params.append(user_id)

    try:
        rowcount = execute_query(query, params=tuple(params), commit=True)
        if rowcount and rowcount > 0:
            logger.info(f"用户信息更新成功: user_id={user_id}")
            return True, "用户信息更新成功"
        return False, "用户不存在"
    except sqlite3.Error as e:
        logger.error(f"更新用户信息失败: {e}")
        return False, f"更新失败: {str(e)}"

def get_user_activity_log(user_id=None, days=7):
    """获取用户活动日志"""
    try:
        if not check_table_exists('system_logs'):
            return []

        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        if user_id:
            query = """
            SELECT sl.*, u.username, u.full_name
            FROM system_logs sl
            JOIN users u ON sl.user_id = u.user_id
            WHERE sl.user_id = %s AND sl.timestamp >= %s
            ORDER BY sl.timestamp DESC
            LIMIT 100
            """
            params = (user_id, cutoff)
        else:
            query = """
            SELECT sl.*, u.username, u.full_name
            FROM system_logs sl
            JOIN users u ON sl.user_id = u.user_id
            WHERE sl.timestamp >= %s
            ORDER BY sl.timestamp DESC
            LIMIT 100
            """
            params = (cutoff,)
        
        return execute_query(query, params=params, fetch_all=True) or []
    except sqlite3.Error as e:
        logger.error(f"获取活动日志失败: {e}")
        return []

def get_all_roles():
    """获取所有角色 - 从DB查询"""
    query = "SELECT role_id, role_name, description FROM roles ORDER BY role_id"
    try:
        result = execute_query(query, fetch_all=True)
        logger.info(f"获取角色列表成功，共 {len(result) if result else 0} 个角色")
        return result or []
    except sqlite3.Error as e:
        logger.error(f"获取角色列表失败: {e}")
        return []

def validate_password_strength(password: str):
    """验证密码强度 - 增强版"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"密码长度至少{PASSWORD_MIN_LENGTH}位"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含数字"
    return True, "密码强度符合要求"

def get_user_permissions():
    """获取当前用户的权限列表"""
    user_role = st.session_state.get('user_role', '')
    return ROLE_PERMISSIONS.get(user_role, [])

def require_permission(permission: str):
    """页面级权限装饰器，用于保护 show() 函数"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not st.session_state.get('logged_in', False):
                st.error("🔒 请先登录以访问此页面。")
                st.stop()
                return
            if not has_permission(permission):
                user_role = st.session_state.get('user_role', '未知角色')
                st.error(f"❌ 权限不足：您的角色（{user_role}）无法访问此功能。")
                st.stop()
                return
            return func(*args, **kwargs)
        return wrapper
    return decorator

def update_user_password(user_id: int, new_password: str):
    """更新用户密码"""
    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        return False, msg

    password_hash = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    query = "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s"
    try:
        rowcount = execute_query(query, params=(password_hash, user_id), commit=True)
        if rowcount and rowcount > 0:
            logger.info(f"密码更新成功: user_id={user_id}")
            return True, "密码更新成功"
        else:
            return False, "用户不存在"
    except sqlite3.Error as e:
        logger.error(f"更新密码失败: {e}")
        return False, f"更新失败: {str(e)}"
