# fix_missing_tables.py
"""
专门修复缺少表的脚本
根据诊断结果，补充缺少的表和数据
"""

import psycopg2
import hashlib
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'mold_management',
    'user': 'postgres',
    'password': 'hy720901'
}

def simple_hash_password(password):
    """使用SHA256哈希密码"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def check_and_create_missing_tables():
    """检查并创建缺少的表"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 开始修复缺少的表...")
        
        # 1. 创建角色表
        print("1. 创建角色表 (roles)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id SERIAL PRIMARY KEY,
                role_name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # 2. 创建模具状态表
        print("2. 创建模具状态表 (mold_statuses)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mold_statuses (
                status_id SERIAL PRIMARY KEY,
                status_name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # 3. 创建模具功能类型表
        print("3. 创建模具功能类型表 (mold_functional_types)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mold_functional_types (
                type_id SERIAL PRIMARY KEY,
                type_name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # 4. 创建存放位置表
        print("4. 创建存放位置表 (storage_locations)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage_locations (
                location_id SERIAL PRIMARY KEY,
                location_name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # 5. 创建借用状态表
        print("5. 创建借用状态表 (loan_statuses)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_statuses (
                status_id SERIAL PRIMARY KEY,
                status_name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # 6. 创建模具借用记录表（如果不存在）
        print("6. 创建模具借用记录表 (mold_loan_records)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mold_loan_records (
                loan_id SERIAL PRIMARY KEY,
                mold_id INTEGER NOT NULL,
                applicant_id INTEGER NOT NULL,
                application_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                approver_id INTEGER,
                approval_timestamp TIMESTAMPTZ,
                loan_out_timestamp TIMESTAMPTZ,
                expected_return_timestamp TIMESTAMPTZ,
                actual_return_timestamp TIMESTAMPTZ,
                loan_status_id INTEGER NOT NULL,
                destination_equipment VARCHAR(100),
                remarks TEXT
            );
        """)
        
        conn.commit()
        print("✅ 所有缺少的表已创建完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

def insert_basic_data():
    """插入基础数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n📝 插入基础数据...")
        
        # 1. 插入角色数据
        print("1. 插入角色数据...")
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
        
        # 2. 插入模具状态数据
        print("2. 插入模具状态数据...")
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
        
        # 3. 插入模具功能类型数据
        print("3. 插入模具功能类型数据...")
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
        
        # 4. 插入存放位置数据
        print("4. 插入存放位置数据...")
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
        
        # 5. 插入借用状态数据
        print("5. 插入借用状态数据...")
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
        
        conn.commit()
        print("✅ 基础数据插入完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 插入基础数据失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

def check_and_fix_users_table():
    """检查并修复用户表结构"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n👥 检查用户表结构...")
        
        # 检查用户表的列
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("现有用户表列:")
        existing_columns = []
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
            existing_columns.append(col[0])
        
        # 检查是否缺少必要的列
        required_columns = [
            'user_id', 'username', 'password_hash', 'full_name', 
            'role_id', 'email', 'is_active', 'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"缺少列: {missing_columns}")
            
            # 尝试添加缺少的列
            if 'role_id' in missing_columns:
                print("添加 role_id 列...")
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER;
                """)
            
            if 'email' in missing_columns:
                print("添加 email 列...")
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(100);
                """)
            
            if 'is_active' in missing_columns:
                print("添加 is_active 列...")
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                """)
            
            if 'created_at' in missing_columns:
                print("添加 created_at 列...")
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
                """)
            
            if 'updated_at' in missing_columns:
                print("添加 updated_at 列...")
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
                """)
        
        # 检查现有用户数据
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"现有用户数量: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT username, full_name FROM users LIMIT 5")
            users = cursor.fetchall()
            print("现有用户:")
            for user in users:
                print(f"  - {user[0]} ({user[1] if user[1] else 'N/A'})")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ 检查用户表失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

def create_admin_user_if_not_exists():
    """如果不存在admin用户则创建"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔑 检查并创建admin用户...")
        
        # 检查admin用户是否存在
        cursor.execute("SELECT user_id, username FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"✅ admin用户已存在 (ID: {admin_user[0]})")
            
            # 检查role_id是否正确设置
            cursor.execute("SELECT role_id FROM users WHERE username = 'admin'")
            role_result = cursor.fetchone()
            
            if not role_result or not role_result[0]:
                print("🔧 修复admin用户的角色...")
                # 获取超级管理员角色ID
                cursor.execute("SELECT role_id FROM roles WHERE role_name = '超级管理员'")
                admin_role = cursor.fetchone()
                
                if admin_role:
                    cursor.execute(
                        "UPDATE users SET role_id = %s WHERE username = 'admin'",
                        (admin_role[0],)
                    )
                    print("✅ admin用户角色已修复")
        else:
            print("🔧 创建admin用户...")
            
            # 获取超级管理员角色ID
            cursor.execute("SELECT role_id FROM roles WHERE role_name = '超级管理员'")
            admin_role = cursor.fetchone()
            
            if not admin_role:
                print("❌ 超级管理员角色不存在")
                return False
            
            # 创建admin用户
            password_hash = simple_hash_password('admin123')
            
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('admin', password_hash, '系统管理员', admin_role[0], 'admin@company.com', True, datetime.now(), datetime.now()))
            
            print("✅ admin用户创建成功")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ 处理admin用户失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

def test_complete_system():
    """测试完整系统"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🧪 测试完整系统...")
        
        # 1. 测试登录
        print("1. 测试admin登录...")
        cursor.execute("""
            SELECT u.user_id, u.username, u.password_hash, u.full_name, r.role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = 'admin' AND u.is_active = true
        """)
        
        user = cursor.fetchone()
        
        if not user:
            print("❌ admin用户不存在或未激活")
            return False
        
        # 验证密码
        stored_hash = user[2]
        test_hash = simple_hash_password('admin123')
        
        if stored_hash == test_hash:
            print(f"✅ admin登录测试成功")
            print(f"   用户信息: {user[3]} ({user[4] or '无角色'})")
        else:
            print("❌ admin密码验证失败")
            return False
        
        # 2. 测试表完整性
        print("2. 测试表完整性...")
        required_tables = ['roles', 'users', 'mold_statuses', 'mold_functional_types', 
                          'storage_locations', 'loan_statuses', 'mold_loan_records']
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"❌ 仍缺少表: {missing_tables}")
            return False
        else:
            print("✅ 所有必需表都存在")
        
        # 3. 测试基础数据
        print("3. 测试基础数据...")
        data_checks = [
            ('roles', 'SELECT COUNT(*) FROM roles'),
            ('mold_statuses', 'SELECT COUNT(*) FROM mold_statuses'),
            ('loan_statuses', 'SELECT COUNT(*) FROM loan_statuses'),
            ('mold_functional_types', 'SELECT COUNT(*) FROM mold_functional_types'),
            ('storage_locations', 'SELECT COUNT(*) FROM storage_locations')
        ]
        
        for table_name, query in data_checks:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"   {table_name}: {count} 条记录")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        return False

def show_final_instructions():
    """显示最终说明"""
    print("\n" + "="*60)
    print("📋 auth.py 文件更新说明")
    print("="*60)
    
    print("\n需要更新 app/utils/auth.py 文件以支持简单哈希登录:")
    print("\n1. 在文件顶部添加:")
    print("   import hashlib")
    
    print("\n2. 添加哈希函数:")
    print("""
def simple_hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
""")
    
    print("3. 更新 login_user 函数，将密码验证部分改为:")
    print("""
# 将原来的 bcrypt 验证替换为:
stored_hash = result['password_hash']
input_hash = simple_hash_password(password)

if stored_hash == input_hash:
    # 登录成功的逻辑
""")

def main():
    """主函数"""
    print("="*60)
    print("🔧 修复缺少表的专用工具")
    print("="*60)
    
    # 1. 创建缺少的表
    if not check_and_create_missing_tables():
        return
    
    # 2. 插入基础数据
    if not insert_basic_data():
        return
    
    # 3. 检查并修复用户表
    if not check_and_fix_users_table():
        return
    
    # 4. 创建admin用户
    if not create_admin_user_if_not_exists():
        return
    
    # 5. 测试完整系统
    if not test_complete_system():
        return
    
    # 6. 显示最终说明
    show_final_instructions()
    
    print("\n" + "="*60)
    print("🎉 修复完成!")
    print("="*60)
    
    print("\n🔑 现在可以使用以下账户登录:")
    print("   用户名: admin")
    print("   密码: admin123")
    print("   角色: 超级管理员")
    
    print("\n📋 下一步:")
    print("   1. 按照上述说明更新 app/utils/auth.py")
    print("   2. 重启 Streamlit: streamlit run app/main.py")
    print("   3. 使用 admin/admin123 登录")

if __name__ == "__main__":
    main()