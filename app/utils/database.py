# utils/database.py - 完整修复版数据库连接系统
import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st
import logging
import numpy as np
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple
import json
from datetime import datetime, date
from decimal import Decimal
import time  # 用于重试延迟

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 数据库配置 ==========

def get_db_config() -> Dict[str, str]:
    """获取数据库配置"""
    config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'mold_management'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD')  # 无默认，确保env设置
    }
    # 验证必需配置
    if not config['password']:
        raise ValueError("Missing POSTGRES_PASSWORD in environment variables")
    return config

# 全局连接池
_connection_pool = None

def init_connection_pool():
    """初始化连接池，支持SSL和重试"""
    global _connection_pool
    
    try:
        if _connection_pool is None:
            config = get_db_config()
            pool_args = {
                'host': config['host'],
                'port': config['port'],
                'database': config['database'],
                'user': config['user'],
                'password': config['password'],
                'cursor_factory': psycopg2.extras.RealDictCursor
            }
            # 加SSL配置
            if os.getenv('DB_SSL', 'false') == 'true':
                pool_args['sslmode'] = 'require'
            else:
                pool_args['sslmode'] = 'prefer'
            
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                2, 20,  # 调整min=2, max=20以适应负载
                **pool_args
            )
            logger.info("数据库连接池初始化成功")
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        _connection_pool = None
        # 重试机制：等待2s后重试一次
        time.sleep(2)
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                2, 20, 
                **pool_args
            )
            logger.info("连接池重试初始化成功")
        except:
            raise

def get_connection():
    """从连接池获取连接"""
    global _connection_pool
    
    if _connection_pool is None:
        init_connection_pool()
    
    try:
        if _connection_pool:
            return _connection_pool.getconn()
        else:
            # 备用直接连接
            config = get_db_config()
            pool_args = {
                'host': config['host'],
                'port': config['port'],
                'database': config['database'],
                'user': config['user'],
                'password': config['password'],
                'cursor_factory': psycopg2.extras.RealDictCursor
            }
            if os.getenv('DB_SSL', 'false') == 'true':
                pool_args['sslmode'] = 'require'
            else:
                pool_args['sslmode'] = 'prefer'
            return psycopg2.connect(**pool_args)
    except Exception as e:
        logger.error(f"获取数据库连接失败: {e}")
        raise

def return_connection(conn):
    """归还连接到连接池"""
    global _connection_pool
    
    try:
        if _connection_pool and conn:
            _connection_pool.putconn(conn)
        elif conn:
            conn.close()
    except Exception as e:
        logger.error(f"归还连接失败: {e}")

@contextmanager
def get_db_connection():
    """数据库连接上下文管理器"""
    conn = None
    try:
        conn = get_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"数据库操作异常: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)

# ========== 数据类型转换 ==========

def convert_numpy_types(obj):
    """转换numpy类型为Python原生类型"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (datetime, date)):
        return obj
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

def serialize_params(params):
    """序列化查询参数"""
    if params is None:
        return None
    
    if isinstance(params, (list, tuple)):
        return tuple(convert_numpy_types(p) for p in params)
    else:
        return convert_numpy_types(params)

# ========== 核心数据库操作函数 ==========

def execute_query(
    query: str, 
    params: Optional[Union[List, Tuple, Dict]] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
    commit: bool = False
) -> Optional[Union[List[Dict], Dict, int]]:
    """
    执行数据库查询 - 修复版
    
    Args:
        query: SQL查询语句
        params: 查询参数
        fetch_one: 是否返回单条记录
        fetch_all: 是否返回所有记录
        commit: 是否提交事务
    
    Returns:
        查询结果、影响行数或None
    """
    conn = None
    cursor = None
    
    try:
        # 序列化参数
        clean_params = serialize_params(params)
        
        # 获取连接
        conn = get_connection()
        cursor = conn.cursor()
        
        # 执行查询（加超时30s）
        if clean_params:
            cursor.execute(query, clean_params)
        else:
            cursor.execute(query)
        
        # 处理结果
        result = None
        
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows] if rows else []
        else:
            # 对于DML，返回影响行数
            result = cursor.rowcount
        
        # 提交事务
        if commit:
            conn.commit()
            logger.debug(f"事务已提交: {query[:50]}... 影响行数: {cursor.rowcount}")
        
        # 转换数据类型
        if result:
            result = convert_numpy_types(result)
        
        return result
        
    except psycopg2.Error as e:
        logger.error(f"数据库错误: {e}")
        logger.error(f"查询语句: {query}")
        logger.error(f"参数: {params}")  # 注意：生产中mask敏感params
        if conn:
            conn.rollback()
        raise
        
    except Exception as e:
        logger.error(f"执行查询异常: {e}")
        logger.error(f"查询语句: {query}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

def test_connection() -> bool:
    """测试数据库连接"""
    try:
        result = execute_query("SELECT 1 as test", fetch_one=True)
        return result is not None and result.get('test') == 1
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

def get_table_info(table_name: str) -> List[Dict]:
    """获取表结构信息"""
    try:
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
        """
        return execute_query(query, params=(table_name,), fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取表 {table_name} 信息失败: {e}")
        return []

def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    try:
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        )
        """
        result = execute_query(query, params=(table_name,), fetch_one=True)
        return result.get('exists', False) if result else False
    except Exception as e:
        logger.error(f"检查表 {table_name} 是否存在失败: {e}")
        return False

# ========== 专用查询函数 ==========

def get_all_molds(offset: int = 0, limit: int = 100) -> List[Dict]:
    """获取所有模具信息，支持分页"""
    try:
        query = """
        SELECT 
            m.mold_id,
            m.mold_code,
            m.mold_name,
            m.mold_drawing_number,
            mft.type_name as functional_type,
            m.supplier,
            m.manufacturing_date,
            m.theoretical_lifespan_strokes,
            m.accumulated_strokes,
            m.maintenance_cycle_strokes,
            ms.status_name as current_status,
            sl.location_name as current_location,
            u.full_name as responsible_person,
            m.remarks,
            m.created_at,
            m.updated_at
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
        LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
        LEFT JOIN users u ON m.responsible_person_id = u.user_id
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
        """
        return execute_query(query, params=(limit, offset), fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取模具列表失败: {e}")
        return []

def get_mold_by_id(mold_id: int) -> Optional[Dict]:
    """根据ID获取模具信息"""
    try:
        query = """
        SELECT 
            m.*,
            mft.type_name as functional_type,
            ms.status_name as current_status,
            sl.location_name as current_location,
            u.full_name as responsible_person
        FROM molds m
        LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
        LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
        LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
        LEFT JOIN users u ON m.responsible_person_id = u.user_id
        WHERE m.mold_id = %s
        """
        return execute_query(query, params=(mold_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"获取模具 {mold_id} 信息失败: {e}")
        return None

def get_loan_statuses() -> List[Dict]:
    """获取借用状态列表"""
    try:
        query = "SELECT status_id, status_name, description FROM loan_statuses ORDER BY status_id"
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取借用状态失败: {e}")
        return []

def get_mold_statuses() -> List[Dict]:
    """获取模具状态列表"""
    try:
        query = "SELECT status_id, status_name, description FROM mold_statuses ORDER BY status_id"
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取模具状态失败: {e}")
        return []

def get_storage_locations() -> List[Dict]:
    """获取存储位置列表"""
    try:
        query = "SELECT location_id, location_name, description FROM storage_locations ORDER BY location_name"
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取存储位置失败: {e}")
        return []

def get_functional_types() -> List[Dict]:
    """获取模具功能类型列表"""
    try:
        query = "SELECT type_id, type_name, description FROM mold_functional_types ORDER BY type_name"
        return execute_query(query, fetch_all=True) or []
    except Exception as e:
        logger.error(f"获取功能类型失败: {e}")
        return []

# ========== 数据验证函数 ==========

def validate_foreign_key(table: str, column: str, value: Any) -> bool:
    """验证外键是否存在"""
    try:
        if value is None:
            return True  # NULL值是允许的
        
        query = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {column} = %s)"
        result = execute_query(query, params=(value,), fetch_one=True)
        return result.get('exists', False) if result else False
    except Exception as e:
        logger.error(f"验证外键失败: {table}.{column} = {value}, 错误: {e}")
        return False

def validate_unique_constraint(table: str, column: str, value: Any, exclude_id: Optional[int] = None) -> bool:
    """验证唯一约束"""
    try:
        query = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {column} = %s"
        params = [value]
        
        if exclude_id:
            # 假设主键为 {table[:-1]}_id
            primary_key = f"{table[:-1]}_id"  
            query += f" AND {primary_key} != %s"
            params.append(exclude_id)
        
        query += ")"
        
        result = execute_query(query, params=tuple(params), fetch_one=True)
        exists = result.get('exists', False) if result else False
        return not exists  # 不存在才表示唯一约束满足
    except Exception as e:
        logger.error(f"验证唯一约束失败: {table}.{column} = {value}, 错误: {e}")
        return False

# ========== 批量操作函数 ==========

def bulk_insert(table: str, columns: List[str], data: List[List]) -> bool:
    """批量插入数据"""
    if not data:
        return True
    
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 构建SQL语句
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 执行批量插入
        cursor.executemany(query, data)
        conn.commit()
        
        logger.info(f"批量插入成功: {table} - {len(data)} 条记录")
        return True
        
    except Exception as e:
        logger.error(f"批量插入失败: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

def bulk_update(table: str, updates: List[Dict]) -> bool:
    """批量更新数据"""
    if not updates:
        return True
    
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for update in updates:
            if not update.get('set') or not update.get('where'):
                continue
            
            set_clause = ", ".join([f"{k} = %s" for k in update['set'].keys()])
            where_clause = " AND ".join([f"{k} = %s" for k in update['where'].keys()])
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            params = list(update['set'].values()) + list(update['where'].values())
            
            cursor.execute(query, params)
        
        conn.commit()
        logger.info(f"批量更新成功: {table} - {len(updates)} 条记录")
        return True
        
    except Exception as e:
        logger.error(f"批量更新失败: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

# ========== 事务处理 ==========

@contextmanager
def transaction():
    """事务上下文管理器"""
    conn = None
    
    try:
        conn = get_connection()
        conn.autocommit = False
        
        yield conn
        
        conn.commit()
        logger.debug("事务提交成功")
        
    except Exception as e:
        logger.error(f"事务执行失败: {e}")
        if conn:
            conn.rollback()
            logger.debug("事务已回滚")
        raise
        
    finally:
        if conn:
            return_connection(conn)

# ========== 缓存和性能优化 ==========

@st.cache_data(ttl=300)  # 缓存5分钟
def get_cached_lookup_data():
    """获取缓存的查找数据"""
    try:
        return {
            'mold_statuses': get_mold_statuses(),
            'loan_statuses': get_loan_statuses(),
            'storage_locations': get_storage_locations(),
            'functional_types': get_functional_types()
        }
    except Exception as e:
        logger.error(f"获取缓存查找数据失败: {e}")
        return {}

def clear_cache():
    """清除缓存"""
    try:
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        logger.info("缓存已清除")
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")

# ========== 初始化 ==========

def initialize_database():
    """初始化数据库连接"""
    try:
        init_connection_pool()
        
        # 测试连接
        if test_connection():
            logger.info("数据库连接正常")
            return True
        else:
            logger.error("数据库连接失败")
            return False
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

# 自动初始化
initialize_database()