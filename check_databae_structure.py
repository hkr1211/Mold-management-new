#!/usr/bin/env python3
"""
检查数据库表结构
"""

import psycopg2
import os
from tabulate import tabulate

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mold_management'),
    'user': os.getenv('DB_USER', 'mold_user'),
    'password': os.getenv('DB_PASSWORD', 'mold_password_123'),
    'port': os.getenv('DB_PORT', '5432')
}

def check_table_structure(table_name):
    """检查指定表的结构"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询表结构
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        if columns:
            print(f"\n=== {table_name} 表结构 ===")
            headers = ['字段名', '数据类型', '允许NULL', '默认值']
            print(tabulate(columns, headers=headers, tablefmt='grid'))
        else:
            print(f"\n❌ 表 {table_name} 不存在")
        
        cursor.close()
        conn.close()
        
        return [col[0] for col in columns]  # 返回字段名列表
        
    except Exception as e:
        print(f"检查表结构失败: {e}")
        return []

def check_molds_table():
    """专门检查molds表"""
    print("=== 检查 molds 表结构 ===")
    
    columns = check_table_structure('molds')
    
    # 检查关键字段是否存在
    required_fields = [
        'mold_id', 'mold_code', 'mold_name', 'supplier',
        'current_status_id', 'current_location_id', 'mold_functional_type_id'
    ]
    
    print(f"\n=== 字段检查结果 ===")
    for field in required_fields:
        status = "✓ 存在" if field in columns else "❌ 缺失"
        print(f"{field}: {status}")
    
    return columns

def check_all_tables():
    """检查所有重要表"""
    important_tables = [
        'molds', 'mold_statuses', 'mold_functional_types', 
        'storage_locations', 'users', 'roles'
    ]
    
    for table in important_tables:
        check_table_structure(table)

def main():
    print("=== 数据库表结构检查工具 ===")
    
    # 检查molds表
    molds_columns = check_molds_table()
    
    # 检查所有重要表
    print(f"\n{'='*50}")
    check_all_tables()
    
    # 如果supplier字段不存在，提供修复建议
    if 'supplier' not in molds_columns:
        print(f"\n=== 修复建议 ===")
        print("supplier字段缺失，您可以：")
        print("1. 添加supplier字段到molds表")
        print("2. 修改查询语句使用现有字段")
        print("3. 重新运行数据库初始化脚本")

if __name__ == "__main__":
    main()