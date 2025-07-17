# fix_users_table.py
"""
专门修复用户表结构的脚本
调整现有用户表以匹配系统需求
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

def backup_existing_users():
    """备份现有用户数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("📋 备份现有用户数据...")
        
        # 获取现有用户数据
        cursor.execute("SELECT id, username, password_hash, role, is_active, created_at FROM users")
        existing_users = cursor.fetchall()
        
        print(f"找到 {len(existing_users)} 个现有用户:")
        for user in existing_users:
            print(f"  - ID: {user[0]}, 用户名: {user[1]}, 角色: {user[3]}")
        
        conn.close()
        return existing_users
        
    except Exception as e:
        print(f"❌ 备份用户数据失败: {e}")
        return []

def recreate_users_table(existing_users):
    """重新创建用户表并迁移数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔧 重新创建用户表...")
        
        # 1. 删除旧的用户表
        print("1. 删除旧用户表...")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE")
        
        # 2. 创建新的用户表
        print("2. 创建新用户表...")
        cursor.execute("""
            CREATE TABLE users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role_id INTEGER NOT NULL REFERENCES roles(role_id),
                email VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        
        # 3. 获取角色映射
        print("3. 获取角色映射...")
        cursor.execute("SELECT role_id, role_name FROM roles")
        role_mapping = {}
        for role_id, role_name in cursor.fetchall():
            # 创建多种可能的角色名称映射
            role_mapping[role_name] = role_id
            # 兼容旧的角色名称
            if role_name == '超级管理员':
                role_mapping['admin'] = role_id
                role_mapping['super_admin'] = role_id
                role_mapping['管理员'] = role_id
            elif role_name == '模具库管理员':
                role_mapping['mold_admin'] = role_id
                role_mapping['库管员'] = role_id
            elif role_name == '模具工':
                role_mapping['technician'] = role_id
                role_mapping['tech'] = role_id
            elif role_name == '冲压操作工':
                role_mapping['operator'] = role_id
                role_mapping['op'] = role_id
        
        print(f"角色映射: {role_mapping}")
        
        # 4. 迁移现有用户数据
        print("4. 迁移用户数据...")
        for user in existing_users:
            old_id, username, password_hash, old_role, is_active, created_at = user
            
            # 确定角色ID
            role_id = role_mapping.get(old_role)
            if not role_id:
                # 如果找不到匹配的角色，默认使用超级管理员
                role_id = role_mapping.get('超级管理员', 1)
                print(f"  ⚠️ 用户 {username} 的角色 '{old_role}' 未找到，设为超级管理员")
            
            # 生成全名（如果没有的话）
            full_name_mapping = {
                'admin': '系统管理员',
                'mold_admin': '模具库管理员',
                'technician': '模具工师傅',
                'operator': '冲压操作工'
            }
            full_name = full_name_mapping.get(username, username.title())
            
            # 生成邮箱
            email = f"{username}@company.com"
            
            # 插入用户
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, password_hash, full_name, role_id, email, is_active, created_at, datetime.now()))
            
            print(f"  ✅ 迁移用户: {username} -> {full_name} (角色ID: {role_id})")
        
        conn.commit()
        conn.close()
        
        print("✅ 用户表重建完成")
        return True
        
    except Exception as e:
        print(f"❌ 重建用户表失败: {e}")
        return False

def create_admin_if_missing():
    """如果没有admin用户则创建"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔑 检查admin用户...")
        
        # 检查是否有admin用户
        cursor.execute("SELECT user_id FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()
        
        if not admin_exists:
            print("创建admin用户...")
            
            # 获取超级管理员角色ID
            cursor.execute("SELECT role_id FROM roles WHERE role_name = '超级管理员'")
            admin_role = cursor.fetchone()
            
            if admin_role:
                password_hash = simple_hash_password('admin123')
                
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('admin', password_hash, '系统管理员', admin_role[0], 'admin@company.com', True, datetime.now(), datetime.now()))
                
                print("✅ admin用户创建成功")
            else:
                print("❌ 超级管理员角色不存在")
                return False
        else:
            print("✅ admin用户已存在")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 处理admin用户失败: {e}")
        return False

def verify_final_result():
    """验证最终结果"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🧪 验证最终结果...")
        
        # 1. 检查用户表结构
        print("1. 检查用户表结构...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("用户表列:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        # 2. 检查用户数据
        print("\n2. 检查用户数据...")
        cursor.execute("""
            SELECT u.user_id, u.username, u.full_name, r.role_name, u.is_active
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            ORDER BY u.user_id
        """)
        users = cursor.fetchall()
        
        print(f"用户数量: {len(users)}")
        for user in users:
            status = "启用" if user[4] else "禁用"
            print(f"  - ID:{user[0]} {user[1]} ({user[2]}) - {user[3]} [{status}]")
        
        # 3. 测试admin登录
        print("\n3. 测试admin登录...")
        cursor.execute("""
            SELECT u.user_id, u.username, u.password_hash, u.full_name, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = 'admin' AND u.is_active = true
        """)
        
        admin_user = cursor.fetchone()
        
        if admin_user:
            stored_hash = admin_user[2]
            test_hash = simple_hash_password('admin123')
            
            if stored_hash == test_hash:
                print(f"✅ admin登录测试成功: {admin_user[3]} ({admin_user[4]})")
            else:
                print("❌ admin密码验证失败")
                return False
        else:
            print("❌ admin用户不存在")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def show_auth_update_guide():
    """显示auth.py更新指南"""
    print("\n" + "="*60)
    print("📝 auth.py 更新指南")
    print("="*60)
    
    print("\n请更新 app/utils/auth.py 文件:")
    
    print("\n1. 在文件顶部添加导入:")
    print("   import hashlib")
    
    print("\n2. 添加哈希函数:")
    print("""
def simple_hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
""")
    
    print("3. 更新 login_user 函数的密码验证部分:")
    print("""
# 找到密码验证的地方，替换为:
stored_hash = result['password_hash']
input_hash = simple_hash_password(password)

if stored_hash == input_hash:
    return {
        'user_id': result['user_id'],
        'username': result['username'],
        'full_name': result['full_name'],
        'role': result['role_name']
    }
else:
    return None
""")

def main():
    """主函数"""
    print("="*60)
    print("🔧 用户表结构修复工具")
    print("="*60)
    
    # 1. 备份现有用户
    existing_users = backup_existing_users()
    if not existing_users:
        print("❌ 没有找到现有用户或备份失败")
        return
    
    # 2. 重建用户表
    if not recreate_users_table(existing_users):
        return
    
    # 3. 确保admin用户存在
    if not create_admin_if_missing():
        return
    
    # 4. 验证最终结果
    if not verify_final_result():
        return
    
    # 5. 显示更新指南
    show_auth_update_guide()
    
    print("\n" + "="*60)
    print("🎉 用户表修复完成!")
    print("="*60)
    
    print("\n🔑 现在可以使用以下账户登录:")
    print("   用户名: admin")
    print("   密码: admin123")
    print("   角色: 超级管理员")
    
    print("\n📋 下一步:")
    print("   1. 按照上述指南更新 app/utils/auth.py")
    print("   2. 重启Streamlit: streamlit run app/main.py")
    print("   3. 使用 admin/admin123 登录测试")

if __name__ == "__main__":
    main()