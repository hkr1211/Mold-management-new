# database_diagnosis_and_init.py
"""
数据库诊断和初始化脚本
用于诊断数据库连接状态、检查表结构、初始化数据
"""

import os
import sys
import psycopg2
import bcrypt
import logging
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 数据库连接参数
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'mold_management'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'hy720901')
}

def test_connection():
    """测试数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        conn.close()
        logging.info(f"✅ 数据库连接成功: {version[0]}")
        return True
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return False

def check_tables_exist():
    """检查主要表是否存在"""
    required_tables = [
        'roles', 'users', 'molds', 'mold_statuses', 
        'mold_functional_types', 'storage_locations',
        'mold_loan_records', 'loan_statuses'
    ]
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询所有表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        logging.info(f"🔍 数据库中存在的表: {existing_tables}")
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logging.warning(f"⚠️ 缺少以下表: {missing_tables}")
            return False, missing_tables
        else:
            logging.info("✅ 所有必需的表都存在")
            return True, []
            
        conn.close()
    except Exception as e:
        logging.error(f"❌ 检查表失败: {e}")
        return False, []

def check_roles_data():
    """检查角色数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role_id, role_name, description FROM roles ORDER BY role_id")
        roles = cursor.fetchall()
        
        if roles:
            logging.info("✅ 角色数据存在:")
            for role in roles:
                logging.info(f"   - ID: {role[0]}, 名称: {role[1]}, 描述: {role[2]}")
        else:
            logging.warning("⚠️ 角色表为空")
            
        conn.close()
        return len(roles) > 0
    except Exception as e:
        logging.error(f"❌ 检查角色数据失败: {e}")
        return False

def check_users_data():
    """检查用户数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.user_id, u.username, u.full_name, r.role_name, u.is_active
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.role_id
            ORDER BY u.user_id
        """)
        users = cursor.fetchall()
        
        if users:
            logging.info("✅ 用户数据存在:")
            for user in users:
                status = "启用" if user[4] else "禁用"
                logging.info(f"   - ID: {user[0]}, 用户名: {user[1]}, 姓名: {user[2]}, 角色: {user[3]}, 状态: {status}")
        else:
            logging.warning("⚠️ 用户表为空")
            
        conn.close()
        return len(users) > 0
    except Exception as e:
        logging.error(f"❌ 检查用户数据失败: {e}")
        return False

def hash_password(password):
    """加密密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_initial_roles():
    """创建初始角色"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 创建角色
        roles_data = [
            ('超级管理员', '系统管理员，拥有所有权限'),
            ('模具库管理员', '负责模具台账管理、借用管理等'),
            ('模具工', '负责模具维修保养工作'),
            ('冲压操作工', '负责模具使用和借用申请')
        ]
        
        for role_name, description in roles_data:
            cursor.execute("""
                INSERT INTO roles (role_name, description) 
                VALUES (%s, %s) 
                ON CONFLICT (role_name) DO NOTHING
            """, (role_name, description))
        
        conn.commit()
        conn.close()
        logging.info("✅ 初始角色创建成功")
        return True
    except Exception as e:
        logging.error(f"❌ 创建初始角色失败: {e}")
        return False

def create_initial_users():
    """创建初始用户"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 获取角色ID
        cursor.execute("SELECT role_id, role_name FROM roles")
        roles = {name: role_id for role_id, name in cursor.fetchall()}
        
        if not roles:
            logging.error("❌ 没有找到角色数据，请先创建角色")
            return False
        
        # 创建用户
        users_data = [
            ('admin', 'admin123', '系统管理员', '超级管理员', 'admin@company.com'),
            ('mold_admin', 'mold123', '模具库管理员', '模具库管理员', 'mold@company.com'),
            ('technician', 'tech123', '模具工师傅', '模具工', 'tech@company.com'),
            ('operator', 'op123', '冲压操作工', '冲压操作工', 'op@company.com')
        ]
        
        for username, password, full_name, role_name, email in users_data:
            if role_name not in roles:
                logging.warning(f"⚠️ 角色 {role_name} 不存在，跳过用户 {username}")
                continue
                
            # 检查用户是否已存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                logging.info(f"ℹ️ 用户 {username} 已存在，跳过")
                continue
            
            # 加密密码
            password_hash = hash_password(password)
            
            # 插入用户
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, password_hash, full_name, roles[role_name], email, True, datetime.now(), datetime.now()))
            
            logging.info(f"✅ 创建用户: {username} ({full_name}) - {role_name}")
        
        conn.commit()
        conn.close()
        logging.info("✅ 初始用户创建成功")
        return True
    except Exception as e:
        logging.error(f"❌ 创建初始用户失败: {e}")
        return False

def create_initial_statuses():
    """创建初始状态数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 模具状态
        mold_statuses = [
            ('闲置', '模具可用状态'),
            ('使用中', '模具正在使用'),
            ('已借出', '模具已被借出'),
            ('维修中', '模具正在维修'),
            ('保养中', '模具正在保养'),
            ('待维修', '模具需要维修'),
            ('待保养', '模具需要保养'),
            ('报废', '模具已报废')
        ]
        
        for status_name, description in mold_statuses:
            cursor.execute("""
                INSERT INTO mold_statuses (status_name, description) 
                VALUES (%s, %s) 
                ON CONFLICT (status_name) DO NOTHING
            """, (status_name, description))
        
        # 借用状态
        loan_statuses = [
            ('待审批', '申请已提交，等待审批'),
            ('已批准', '申请已批准，等待领用'),
            ('已领用', '模具已领用'),
            ('已归还', '模具已归还'),
            ('已驳回', '申请被驳回'),
            ('逾期', '超过预期归还时间')
        ]
        
        for status_name, description in loan_statuses:
            cursor.execute("""
                INSERT INTO loan_statuses (status_name, description) 
                VALUES (%s, %s) 
                ON CONFLICT (status_name) DO NOTHING
            """, (status_name, description))
        
        # 模具功能类型
        functional_types = [
            ('落料模', '用于材料下料的模具'),
            ('一引模', '第一道拉伸成型模具'),
            ('二引模', '第二道拉伸成型模具'),
            ('三引模', '第三道拉伸成型模具'),
            ('四引模', '第四道拉伸成型模具'),
            ('切边模', '用于产品切边的模具')
        ]
        
        for type_name, description in functional_types:
            cursor.execute("""
                INSERT INTO mold_functional_types (type_name, description) 
                VALUES (%s, %s) 
                ON CONFLICT (type_name) DO NOTHING
            """, (type_name, description))
        
        # 存放位置
        locations = [
            ('模具库A1', 'A区第1排货架'),
            ('模具库A2', 'A区第2排货架'),
            ('模具库A3', 'A区第3排货架'),
            ('模具库B1', 'B区第1排货架'),
            ('模具库B2', 'B区第2排货架'),
            ('模具库B3', 'B区第3排货架'),
            ('维修车间', '维修保养区域'),
            ('生产车间1', '1号生产车间'),
            ('生产车间2', '2号生产车间')
        ]
        
        for location_name, description in locations:
            cursor.execute("""
                INSERT INTO storage_locations (location_name, description) 
                VALUES (%s, %s) 
                ON CONFLICT (location_name) DO NOTHING
            """, (location_name, description))
        
        conn.commit()
        conn.close()
        logging.info("✅ 初始状态数据创建成功")
        return True
    except Exception as e:
        logging.error(f"❌ 创建初始状态数据失败: {e}")
        return False

def run_diagnosis():
    """运行完整诊断"""
    print("=" * 60)
    print("🔍 模具管理系统数据库诊断工具")
    print("=" * 60)
    
    # 1. 测试连接
    print("\n1. 测试数据库连接...")
    if not test_connection():
        print("❌ 数据库连接失败，请检查配置")
        return False
    
    # 2. 检查表结构
    print("\n2. 检查表结构...")
    tables_exist, missing_tables = check_tables_exist()
    if not tables_exist:
        print(f"❌ 缺少必要的表: {missing_tables}")
        print("💡 请运行数据库初始化脚本: python -c \"from database_diagnosis_and_init import run_initialization; run_initialization()\"")
        return False
    
    # 3. 检查角色数据
    print("\n3. 检查角色数据...")
    if not check_roles_data():
        print("❌ 角色数据缺失")
        return False
    
    # 4. 检查用户数据
    print("\n4. 检查用户数据...")
    if not check_users_data():
        print("❌ 用户数据缺失")
        return False
    
    print("\n✅ 诊断完成 - 数据库状态正常！")
    print("\n🔑 默认登录账户:")
    print("   - 超级管理员: admin / admin123")
    print("   - 模具库管理员: mold_admin / mold123")
    print("   - 模具工: technician / tech123")
    print("   - 冲压操作工: operator / op123")
    
    return True

def run_initialization():
    """运行数据库初始化"""
    print("=" * 60)
    print("🚀 模具管理系统数据库初始化工具")
    print("=" * 60)
    
    # 1. 测试连接
    print("\n1. 测试数据库连接...")
    if not test_connection():
        print("❌ 数据库连接失败，请检查以下配置:")
        print(f"   Host: {DB_CONFIG['host']}")
        print(f"   Port: {DB_CONFIG['port']}")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   User: {DB_CONFIG['user']}")
        return False
    
    # 2. 创建角色
    print("\n2. 创建初始角色...")
    if not create_initial_roles():
        return False
    
    # 3. 创建状态数据
    print("\n3. 创建初始状态数据...")
    if not create_initial_statuses():
        return False
    
    # 4. 创建用户
    print("\n4. 创建初始用户...")
    if not create_initial_users():
        return False
    
    print("\n🎉 数据库初始化完成！")
    print("\n🔑 默认登录账户:")
    print("   - 超级管理员: admin / admin123")
    print("   - 模具库管理员: mold_admin / mold123")
    print("   - 模具工: technician / tech123")
    print("   - 冲压操作工: operator / op123")
    print("\n💡 现在可以使用这些账户登录系统了！")
    
    return True

def test_login(username, password):
    """测试登录功能"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询用户
        cursor.execute("""
            SELECT u.user_id, u.username, u.password_hash, u.full_name, r.role_name, u.is_active
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s AND u.is_active = true
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 用户 {username} 不存在或已被禁用")
            return False
        
        # 验证密码
        stored_password_hash = user[2]
        if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
            print(f"✅ 用户 {username} 登录验证成功")
            print(f"   - ID: {user[0]}")
            print(f"   - 姓名: {user[3]}")
            print(f"   - 角色: {user[4]}")
            return True
        else:
            print(f"❌ 用户 {username} 密码错误")
            return False
            
        conn.close()
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")
        return False

def main():
    """主函数"""
    print("模具管理系统数据库工具")
    print("1. 运行诊断")
    print("2. 初始化数据库")
    print("3. 测试登录")
    print("4. 退出")
    
    while True:
        choice = input("\n请选择操作 (1-4): ").strip()
        
        if choice == '1':
            run_diagnosis()
        elif choice == '2':
            run_initialization()
        elif choice == '3':
            username = input("输入用户名: ").strip()
            password = input("输入密码: ").strip()
            test_login(username, password)
        elif choice == '4':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请输入 1-4")

if __name__ == "__main__":
    main()