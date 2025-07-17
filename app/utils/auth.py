# app/utils/auth.py - 完整修复版

import streamlit as st
import bcrypt
from utils.database import execute_query
import logging
import json
import re  # 用于密码复杂度验证
import time  # 用于登录尝试延迟

# 配置日志，与database.py统一
logging.basicConfig(level=logging.INFO)
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
                except Exception as e:
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
            
    except Exception as e:
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

def login_user(username: str, password: str):
    """用户登录 - 加尝试限制"""
    if 'login_attempts' not in st.session_state:
        st.session_state['login_attempts'] = 0
        st.session_state['last_attempt_time'] = time.time()
    
    # 检查锁定
    if st.session_state['login_attempts'] >= 5:
        if time.time() - st.session_state['last_attempt_time'] < 300:  # 5分钟锁定
            logger.warning(f"登录尝试过多，锁定: {username}")
            return None
        else:
            # 超时重置
            st.session_state['login_attempts'] = 0
    
    user_info = check_password(username, password)
    
    if user_info:
        logger.info(f"登录成功: {username}")
        # 设置会话
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user_info['user_id']
        st.session_state['username'] = user_info['username']
        st.session_state['full_name'] = user_info.get('full_name', user_info['username'])
        st.session_state['user_role'] = user_info['role']
        
        # 重置尝试
        st.session_state['login_attempts'] = 0
        
        # 记录日志
        try:
            log_user_action('LOGIN', 'system', username)
        except Exception as e:
            logger.error(f"记录登录日志失败: {e}")
        
        return user_info
    else:
        st.session_state['login_attempts'] += 1
        st.session_state['last_attempt_time'] = time.time()
        logger.warning(f"登录失败: {username}，尝试次数: {st.session_state['login_attempts']}")
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
        check_query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'system_logs'
        )
        """
        
        table_exists = execute_query(check_query, fetch_one=True)
        if not table_exists or not table_exists.get('exists'):
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
    except Exception as e:
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
    
    # 获取role_id
    role_query = "SELECT role_id FROM roles WHERE role_name = %s"
    role_result = execute_query(role_query, params=(role_name,), fetch_one=True)
    
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
    except Exception as e:
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
    except Exception as e:
        logger.error(f"更新用户状态失败: {e}")
        return False, f"更新失败: {str(e)}"

def get_user_activity_log(user_id=None, days=7):
    """获取用户活动日志"""
    try:
        check_query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'system_logs'
        )
        """
        
        table_exists = execute_query(check_query, fetch_one=True)
        if not table_exists or not table_exists.get('exists'):
            return []
        
        if user_id:
            query = """
            SELECT sl.*, u.username, u.full_name
            FROM system_logs sl
            JOIN users u ON sl.user_id = u.user_id
            WHERE sl.user_id = %s AND sl.timestamp >= NOW() - INTERVAL '%s days'
            ORDER BY sl.timestamp DESC
            LIMIT 100
            """
            params = (user_id, days)
        else:
            query = """
            SELECT sl.*, u.username, u.full_name
            FROM system_logs sl
            JOIN users u ON sl.user_id = u.user_id
            WHERE sl.timestamp >= NOW() - INTERVAL '%s days'
            ORDER BY sl.timestamp DESC
            LIMIT 100
            """
            params = (days,)
        
        return execute_query(query, params=params, fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取活动日志失败: {e}")
        return []

def get_all_roles():
    """获取所有角色 - 从DB查询"""
    query = "SELECT role_id, role_name, description FROM roles ORDER BY role_id"
    try:
        result = execute_query(query, fetch_all=True)
        logger.info(f"获取角色列表成功，共 {len(result) if result else 0} 个角色")
        return result or []
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        return []

def validate_password_strength(password: str):
    """验证密码强度 - 增强版"""
    if len(password) < 8:
        return False, "密码长度至少8位"
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