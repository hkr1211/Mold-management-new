#!/usr/bin/env python3
"""
修复数据库表结构的脚本
添加缺失的字段
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

def check_and_add_missing_columns():
    """检查并添加缺失的列"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("检查 molds 表结构...")
        
        # 检查当前表的所有字段
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'molds'
            ORDER BY ordinal_position
        """)
        existing_columns = {row[0]: row[1] for row in cursor.fetchall()}
        print(f"当前字段: {list(existing_columns.keys())}")
        
        # 需要的字段列表
        required_columns = {
            'mold_id': 'SERIAL PRIMARY KEY',
            'mold_code': 'VARCHAR(100) UNIQUE NOT NULL',
            'mold_name': 'VARCHAR(255) NOT NULL',
            'mold_drawing_number': 'VARCHAR(100)',
            'mold_functional_type_id': 'INTEGER REFERENCES mold_functional_types(type_id)',
            'supplier': 'VARCHAR(255)',  # 这是缺失的字段
            'manufacturing_date': 'DATE',
            'acceptance_date': 'DATE',
            'theoretical_lifespan_strokes': 'INTEGER',
            'accumulated_strokes': 'INTEGER DEFAULT 0',
            'maintenance_cycle_strokes': 'INTEGER',
            'current_status_id': 'INTEGER NOT NULL REFERENCES mold_statuses(status_id)',
            'current_location_id': 'INTEGER REFERENCES storage_locations(location_id)',
            'responsible_person_id': 'INTEGER REFERENCES users(user_id)',
            'design_drawing_link': 'TEXT',
            'image_path': 'TEXT',
            'remarks': 'TEXT',
            'project_number': 'VARCHAR(100)',
            'associated_equipment_number': 'VARCHAR(100)',
            'entry_date': 'DATE DEFAULT CURRENT_DATE',
            'created_at': 'TIMESTAMPTZ NOT NULL DEFAULT NOW()',
            'updated_at': 'TIMESTAMPTZ NOT NULL DEFAULT NOW()'
        }
        
        # 检查并添加缺失的字段
        missing_columns = []
        for column_name, column_def in required_columns.items():
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_def))
        
        if missing_columns:
            print(f"\n发现 {len(missing_columns)} 个缺失字段:")
            for col_name, col_def in missing_columns:
                print(f"  - {col_name}")
            
            print("\n开始添加缺失字段...")
            for col_name, col_def in missing_columns:
                try:
                    # 对于某些特殊字段，需要特殊处理
                    if col_name == 'supplier':
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} VARCHAR(255)"
                    elif col_name == 'entry_date':
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} DATE DEFAULT CURRENT_DATE"
                    elif col_name == 'created_at':
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} TIMESTAMPTZ DEFAULT NOW()"
                        # 添加后设置为NOT NULL
                        not_null_sql = f"ALTER TABLE molds ALTER COLUMN {col_name} SET NOT NULL"
                    elif col_name == 'updated_at':
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} TIMESTAMPTZ DEFAULT NOW()"
                        not_null_sql = f"ALTER TABLE molds ALTER COLUMN {col_name} SET NOT NULL"
                    elif 'DEFAULT' in col_def and 'NOT NULL' in col_def:
                        # 先添加列，再设置NOT NULL
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} {col_def.replace('NOT NULL', '').strip()}"
                        not_null_sql = f"ALTER TABLE molds ALTER COLUMN {col_name} SET NOT NULL"
                    else:
                        add_sql = f"ALTER TABLE molds ADD COLUMN {col_name} {col_def.split(' REFERENCES')[0]}"
                    
                    print(f"添加字段: {col_name}")
                    cursor.execute(add_sql)
                    
                    # 如果需要设置NOT NULL约束
                    if col_name in ['created_at', 'updated_at'] or ('NOT NULL' in col_def and 'DEFAULT' in col_def):
                        if 'not_null_sql' in locals():
                            cursor.execute(not_null_sql)
                    
                    conn.commit()
                    print(f"✓ 成功添加字段: {col_name}")
                    
                except Exception as e:
                    print(f"✗ 添加字段 {col_name} 失败: {e}")
                    conn.rollback()
        else:
            print("✓ 所有必需字段都已存在")
        
        # 检查并修复mold_usage_records表
        print("\n检查 mold_usage_records 表...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'mold_usage_records'
        """)
        usage_columns = [row[0] for row in cursor.fetchall()]
        
        usage_required_columns = [
            'usage_id', 'mold_id', 'operator_id', 'equipment_id',
            'production_order_number', 'product_id_produced', 
            'start_timestamp', 'end_timestamp', 'strokes_this_session',
            'produced_quantity', 'qualified_quantity', 'notes', 'recorded_at'
        ]
        
        usage_missing = [col for col in usage_required_columns if col not in usage_columns]
        
        if usage_missing:
            print(f"mold_usage_records 表缺失字段: {usage_missing}")
            # 添加缺失字段的SQL
            usage_additions = {
                'operator_id': 'ALTER TABLE mold_usage_records ADD COLUMN operator_id INTEGER REFERENCES users(user_id)',
                'equipment_id': 'ALTER TABLE mold_usage_records ADD COLUMN equipment_id VARCHAR(100)',
                'production_order_number': 'ALTER TABLE mold_usage_records ADD COLUMN production_order_number VARCHAR(100)',
                'product_id_produced': 'ALTER TABLE mold_usage_records ADD COLUMN product_id_produced INTEGER REFERENCES products(product_id)',
                'start_timestamp': 'ALTER TABLE mold_usage_records ADD COLUMN start_timestamp TIMESTAMPTZ',
                'end_timestamp': 'ALTER TABLE mold_usage_records ADD COLUMN end_timestamp TIMESTAMPTZ',
                'strokes_this_session': 'ALTER TABLE mold_usage_records ADD COLUMN strokes_this_session INTEGER DEFAULT 0',
                'produced_quantity': 'ALTER TABLE mold_usage_records ADD COLUMN produced_quantity INTEGER',
                'qualified_quantity': 'ALTER TABLE mold_usage_records ADD COLUMN qualified_quantity INTEGER',
                'notes': 'ALTER TABLE mold_usage_records ADD COLUMN notes TEXT',
                'recorded_at': 'ALTER TABLE mold_usage_records ADD COLUMN recorded_at TIMESTAMPTZ DEFAULT NOW()'
            }
            
            for col in usage_missing:
                if col in usage_additions:
                    try:
                        cursor.execute(usage_additions[col])
                        conn.commit()
                        print(f"✓ 添加 mold_usage_records.{col}")
                    except Exception as e:
                        print(f"✗ 添加 mold_usage_records.{col} 失败: {e}")
                        conn.rollback()
        
        # 最终验证
        print("\n最终验证...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'molds'
            ORDER BY ordinal_position
        """)
        final_columns = [row[0] for row in cursor.fetchall()]
        print(f"molds表最终字段: {final_columns}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"修复表结构失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 数据库表结构修复工具 ===\n")
    
    # 测试连接
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False
    
    # 修复表结构
    if check_and_add_missing_columns():
        print("\n=== 表结构修复完成! ===")
        print("现在可以重启应用程序，问题应该已解决。")
        return True
    else:
        print("\n=== 表结构修复失败! ===")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)