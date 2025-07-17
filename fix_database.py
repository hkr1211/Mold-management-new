#!/usr/bin/env python3
"""
数据库修复脚本
用于修复缺失的表字段
"""

import psycopg2
import os
import sys

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mold_management'),
    'user': os.getenv('DB_USER', 'mold_user'),
    'password': os.getenv('DB_PASSWORD', 'mold_password_123'),
    'port': os.getenv('DB_PORT', '5432')
}

def fix_mold_usage_records_table():
    """修复mold_usage_records表的缺失字段"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("检查并修复 mold_usage_records 表...")
        
        # 获取当前表的所有字段
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'mold_usage_records'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"当前存在的字段: {existing_columns}")
        
        # 需要检查的字段列表
        required_fields = [
            ("operator_id", "INTEGER REFERENCES users(user_id)"),
            ("product_id_produced", "INTEGER REFERENCES products(product_id)"),
            ("equipment_id", "VARCHAR(100)"),
            ("production_order_number", "VARCHAR(100)"),
            ("start_timestamp", "TIMESTAMPTZ NOT NULL"),
            ("end_timestamp", "TIMESTAMPTZ"),
            ("strokes_this_session", "INTEGER NOT NULL"),
            ("produced_quantity", "INTEGER"),
            ("qualified_quantity", "INTEGER"),
            ("notes", "TEXT"),
            ("recorded_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        ]
        
        # 添加缺失的字段
        for field_name, field_type in required_fields:
            if field_name not in existing_columns:
                print(f"添加缺失字段: {field_name}")
                try:
                    # 对于NOT NULL字段，需要特殊处理
                    if "NOT NULL" in field_type and "DEFAULT" not in field_type:
                        if field_name == "start_timestamp":
                            cursor.execute(f"""
                                ALTER TABLE mold_usage_records 
                                ADD COLUMN {field_name} {field_type.replace('NOT NULL', '')}
                            """)
                            cursor.execute(f"""
                                UPDATE mold_usage_records 
                                SET {field_name} = COALESCE(recorded_at, NOW())
                                WHERE {field_name} IS NULL
                            """)
                            cursor.execute(f"""
                                ALTER TABLE mold_usage_records 
                                ALTER COLUMN {field_name} SET NOT NULL
                            """)
                        elif field_name == "strokes_this_session":
                            cursor.execute(f"""
                                ALTER TABLE mold_usage_records 
                                ADD COLUMN {field_name} INTEGER DEFAULT 0
                            """)
                            cursor.execute(f"""
                                ALTER TABLE mold_usage_records 
                                ALTER COLUMN {field_name} SET NOT NULL
                            """)
                    else:
                        cursor.execute(f"""
                            ALTER TABLE mold_usage_records 
                            ADD COLUMN {field_name} {field_type}
                        """)
                    conn.commit()
                    print(f"✓ 成功添加字段: {field_name}")
                except Exception as e:
                    print(f"✗ 添加字段 {field_name} 失败: {e}")
                    conn.rollback()
        
        # 再次检查表结构
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'mold_usage_records'
            ORDER BY ordinal_position
        """)
        
        print("\n修复后的表结构:")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"{row[0]:30} {row[1]:20} {row[2]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"修复表结构失败: {e}")
        return False

def check_all_tables():
    """检查所有表的完整性"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查所有关键表是否存在
        tables_to_check = [
            'users', 'roles', 'molds', 'mold_parts', 
            'mold_usage_records', 'mold_loan_records',
            'mold_maintenance_logs', 'products'
        ]
        
        print("\n检查表的存在性:")
        print("-" * 40)
        for table in tables_to_check:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table,)
            )
            exists = cursor.fetchone()[0]
            status = "✓ 存在" if exists else "✗ 不存在"
            print(f"{table:25} {status}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查表失败: {e}")

def main():
    """主函数"""
    print("=== 数据库修复工具 ===\n")
    
    # 检查数据库连接
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False
    
    # 检查所有表
    check_all_tables()
    
    # 修复mold_usage_records表
    print("\n" + "=" * 60)
    if fix_mold_usage_records_table():
        print("\n✓ 数据库修复完成！")
    else:
        print("\n✗ 数据库修复失败！")
    
    return True

if __name__ == "__main__":
    main()