#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复借用管理系统的数据库问题 - Python版本
运行方式: python fix_loan_status.py
"""

import psycopg2
import psycopg2.extras
import os
import sys

# 设置正确的编码
import locale
if sys.platform.startswith('win'):
    locale.setlocale(locale.LC_ALL, 'C')

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mold_management'),
    'user': os.getenv('DB_USER', 'mold_user'),
    'password': os.getenv('DB_PASSWORD', 'mold_password_123'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'client_encoding': 'utf8'
}

def test_database_connection():
    """测试数据库连接并处理编码问题"""
    print("=== 测试数据库连接 ===")
    
    # 尝试不同的连接配置
    connection_configs = [
        # 配置1: 标准UTF-8连接
        {**DB_CONFIG, 'client_encoding': 'utf8'},
        
        # 配置2: 使用SQL_ASCII编码
        {**DB_CONFIG, 'client_encoding': 'SQL_ASCII'},
        
        # 配置3: 不指定编码
        {k: v for k, v in DB_CONFIG.items() if k != 'client_encoding'},
        
        # 配置4: 使用GBK编码(Windows中文)
        {**DB_CONFIG, 'client_encoding': 'GBK'},
    ]
    
    for i, config in enumerate(connection_configs, 1):
        try:
            print(f"\n尝试连接配置 {i}:")
            if 'client_encoding' in config:
                print(f"  编码: {config['client_encoding']}")
            else:
                print(f"  编码: 默认")
                
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            print(f"✓ 连接成功!")
            print(f"  PostgreSQL版本: {version[:50]}...")
            
            # 返回成功的配置
            return config
            
        except Exception as e:
            print(f"✗ 配置 {i} 失败: {str(e)[:100]}...")
            continue
    
    return None
    """修复借用状态数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("=== 修复借用状态数据 ===\n")
        
        # 1. 检查当前状态
        print("1. 检查当前loan_statuses表数据:")
        cursor.execute("SELECT status_id, status_name FROM loan_statuses ORDER BY status_id")
        current_statuses = cursor.fetchall()
        
        if current_statuses:
            for status in current_statuses:
                print(f"   {status['status_id']}: {status['status_name']}")
        else:
            print("   表为空")
        
        # 2. 检查缺少的状态
        print("\n2. 检查缺少的状态:")
        required_statuses = [
            ('待审批', '申请已提交，等待审批'),
            ('已批准', '申请已批准，等待处理'),
            ('已批准待借出', '申请已批准，等待借出'),
            ('已借出', '模具已借出使用'),
            ('已归还', '模具已归还'),
            ('已驳回', '申请被驳回'),
            ('逾期', '超过预期归还时间'),
            ('外借申请中', '申请处理中，模具预留状态')
        ]
        
        existing_names = [s['status_name'] for s in current_statuses]
        missing_statuses = [s for s in required_statuses if s[0] not in existing_names]
        
        if missing_statuses:
            print("   缺少以下状态:")
            for status_name, desc in missing_statuses:
                print(f"   - {status_name}")
        else:
            print("   所有必需状态都存在")
        
        # 3. 插入缺少的状态
        if missing_statuses:
            print("\n3. 插入缺少的状态:")
            for status_name, description in missing_statuses:
                try:
                    cursor.execute(
                        "INSERT INTO loan_statuses (status_name, description) VALUES (%s, %s)",
                        (status_name, description)
                    )
                    print(f"   ✓ 已添加: {status_name}")
                    conn.commit()
                except psycopg2.IntegrityError:
                    print(f"   - 状态 {status_name} 已存在，跳过")
                    conn.rollback()
                    continue
        
        # 4. 检查并修复mold_statuses
        print("\n4. 检查模具状态:")
        mold_statuses = [
            ('外借申请中', '模具正在处理借用申请'),
            ('已预定', '模具已预定待借出'),
            ('已借出', '模具已借出使用')
        ]
        
        cursor.execute("SELECT status_name FROM mold_statuses")
        existing_mold_statuses = [row['status_name'] for row in cursor.fetchall()]
        
        for status_name, description in mold_statuses:
            if status_name not in existing_mold_statuses:
                try:
                    cursor.execute(
                        "INSERT INTO mold_statuses (status_name, description) VALUES (%s, %s)",
                        (status_name, description)
                    )
                    print(f"   ✓ 已添加模具状态: {status_name}")
                    conn.commit()
                except psycopg2.IntegrityError:
                    print(f"   - 模具状态 {status_name} 已存在，跳过")
                    conn.rollback()
                    continue
        
        # 5. 验证结果
        print("\n5. 验证修复结果:")
        cursor.execute("SELECT status_id, status_name FROM loan_statuses ORDER BY status_id")
        final_statuses = cursor.fetchall()
        
        print("   最终loan_statuses表数据:")
        for status in final_statuses:
            print(f"   {status['status_id']}: {status['status_name']}")
        
        # 6. 检查孤立记录
        print("\n6. 检查孤立的借用记录:")
        cursor.execute("""
            SELECT COUNT(*) as orphaned_count
            FROM mold_loan_records mlr
            LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
            WHERE ls.status_id IS NULL
        """)
        result = cursor.fetchone()
        orphaned_count = result['orphaned_count'] if result else 0
        
        if orphaned_count > 0:
            print(f"   ⚠️  发现 {orphaned_count} 条孤立的借用记录")
            
            # 显示孤立记录详情
            cursor.execute("""
                SELECT mlr.loan_id, mlr.loan_status_id, mlr.mold_id
                FROM mold_loan_records mlr
                LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
                WHERE ls.status_id IS NULL
                LIMIT 5
            """)
            orphaned_records = cursor.fetchall()
            
            print("   孤立记录详情:")
            for record in orphaned_records:
                print(f"   - 借用ID: {record['loan_id']}, 状态ID: {record['loan_status_id']}, 模具ID: {record['mold_id']}")
            
            # 提供修复建议
            print("\n   修复建议:")
            print("   1. 检查这些记录的正确状态")
            print("   2. 手动更新为正确的状态ID")
            print("   3. 或删除这些无效记录")
        else:
            print("   ✓ 没有发现孤立记录")
        
        cursor.close()
        conn.close()
        
        print("\n=== 修复完成 ===")
        return True
        
    except Exception as e:
        print(f"修复失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False

def test_status_lookup(db_config):
    """测试状态查找功能"""
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("\n=== 测试状态查找 ===")
        
        test_statuses = ['待审批', '已批准', '已借出', '已归还', '已驳回']
        
        for status_name in test_statuses:
            cursor.execute("SELECT status_id FROM loan_statuses WHERE status_name = %s", (status_name,))
            result = cursor.fetchone()
            
            if result:
                print(f"✓ {status_name}: ID = {result['status_id']}")
            else:
                print(f"✗ {status_name}: 未找到")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"测试失败: {e}")

def create_test_loan_record(db_config):
    """创建测试借用记录"""
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("\n=== 创建测试数据 ===")
        
        # 检查是否有可用的模具和用户
        cursor.execute("SELECT mold_id FROM molds LIMIT 1")
        mold = cursor.fetchone()
        
        cursor.execute("SELECT user_id FROM users LIMIT 1")
        user = cursor.fetchone()
        
        cursor.execute("SELECT status_id FROM loan_statuses WHERE status_name = '待审批'")
        status = cursor.fetchone()
        
        if mold and user and status:
            # 检查是否已有测试记录
            cursor.execute("""
                SELECT loan_id FROM mold_loan_records 
                WHERE mold_id = %s AND applicant_id = %s
            """, (mold['mold_id'], user['user_id']))
            
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO mold_loan_records 
                    (mold_id, applicant_id, loan_status_id, destination_equipment, remarks)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING loan_id
                """, (
                    mold['mold_id'], 
                    user['user_id'], 
                    status['status_id'],
                    '测试设备001',
                    '测试借用记录'
                ))
                
                loan_result = cursor.fetchone()
                loan_id = loan_result['loan_id'] if loan_result else None
                conn.commit()
                print(f"✓ 创建测试借用记录，ID: {loan_id}")
            else:
                print("✓ 测试借用记录已存在")
        else:
            print("✗ 缺少必要的基础数据（模具、用户或状态）")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"创建测试数据失败: {e}")

def check_table_structure(db_config):
    """检查表结构是否正确"""
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("\n=== 检查表结构 ===")
        
        # 检查mold_loan_records表结构
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'mold_loan_records'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print("mold_loan_records表字段:")
        for col in columns:
            print(f"   {col[0]} - {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        
        # 检查必要字段
        required_fields = ['loan_id', 'mold_id', 'applicant_id', 'loan_status_id']
        existing_fields = [col[0] for col in columns]
        
        missing_fields = [field for field in required_fields if field not in existing_fields]
        
        if missing_fields:
            print(f"\n⚠️  缺少必要字段: {', '.join(missing_fields)}")
            print("请运行以下SQL命令添加缺失字段:")
            for field in missing_fields:
                if field == 'applicant_id':
                    print(f"   ALTER TABLE mold_loan_records ADD COLUMN {field} INTEGER REFERENCES users(user_id);")
                elif field == 'loan_status_id':
                    print(f"   ALTER TABLE mold_loan_records ADD COLUMN {field} INTEGER REFERENCES loan_statuses(status_id);")
        else:
            print("✓ 所有必要字段都存在")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查表结构失败: {e}")

def main():
    """主函数"""
    print("蕴杰金属冲压模具管理系统 - 借用状态修复工具\n")
    
    # 测试数据库连接
    working_config = test_database_connection()
    if not working_config:
        print("\n❌ 无法连接到数据库，请检查以下内容:")
        print("1. PostgreSQL服务是否正在运行")
        print("2. Docker容器是否启动 (docker-compose up -d)")
        print("3. 数据库配置是否正确")
        print("4. 防火墙设置")
        print("\n可以尝试手动连接测试:")
        print(f"psql -h {DB_CONFIG['host']} -p {DB_CONFIG['port']} -U {DB_CONFIG['user']} -d {DB_CONFIG['database']}")
        return False
    
    # 检查表结构
    check_table_structure(working_config)
    
    # 修复状态数据
    if fix_loan_status_data(working_config):
        # 测试状态查找
        test_status_lookup(working_config)
        
        # 创建测试数据
        create_test_loan_record(working_config)
        
        print("\n✅ 修复完成！现在可以重新运行借用管理功能。")
        print("\n建议:")
        print("1. 重启Streamlit应用")
        print("2. 重新登录系统")
        print("3. 测试借用管理功能")
        return True
    else:
        print("\n❌ 修复失败，请检查错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)