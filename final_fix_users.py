# final_fix_users.py
"""
最终修复：重置用户密码和角色
确保所有用户都能正常登录
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

def fix_user_passwords_and_roles():
    """修复用户密码和角色"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 修复用户密码和角色...")
        
        # 获取角色映射
        cursor.execute("SELECT role_id, role_name FROM roles")
        role_mapping = {}
        for role_id, role_name in cursor.fetchall():
            role_mapping[role_name] = role_id
        
        print(f"可用角色: {list(role_mapping.keys())}")
        
        # 定义正确的用户配置
        user_configs = [
            {
                'username': 'admin',
                'password': 'admin123',
                'full_name': '系统管理员',
                'role_name': '超级管理员',
                'email': 'admin@company.com'
            },
            {
                'username': 'mold_admin',
                'password': 'mold123',
                'full_name': '模具库管理员',
                'role_name': '模具库管理员',
                'email': 'mold@company.com'
            },
            {
                'username': 'technician',
                'password': 'tech123',
                'full_name': '模具工师傅',
                'role_name': '模具工',
                'email': 'tech@company.com'
            },
            {
                'username': 'operator',
                'password': 'op123',
                'full_name': '冲压操作工',
                'role_name': '冲压操作工',
                'email': 'op@company.com'
            }
        ]
        
        # 更新每个用户
        for user_config in user_configs:
            username = user_config['username']
            password = user_config['password']
            full_name = user_config['full_name']
            role_name = user_config['role_name']
            email = user_config['email']
            
            # 获取角色ID
            role_id = role_mapping.get(role_name)
            if not role_id:
                print(f"❌ 角色 '{role_name}' 不存在")
                continue
            
            # 生成新的密码哈希
            password_hash = simple_hash_password(password)
            
            # 检查用户是否存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                # 更新现有用户
                cursor.execute("""
                    UPDATE users SET 
                        password_hash = %s,
                        full_name = %s,
                        role_id = %s,
                        email = %s,
                        updated_at = %s
                    WHERE username = %s
                """, (password_hash, full_name, role_id, email, datetime.now(), username))
                
                print(f"✅ 更新用户: {username} -> {full_name} ({role_name})")
            else:
                # 创建新用户
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, role_id, email, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (username, password_hash, full_name, role_id, email, True, datetime.now(), datetime.now()))
                
                print(f"✅ 创建用户: {username} -> {full_name} ({role_name})")
        
        conn.commit()
        conn.close()
        
        print("✅ 用户密码和角色修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

def test_all_logins():
    """测试所有用户登录"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🧪 测试所有用户登录...")
        
        # 测试用户列表
        test_users = [
            ('admin', 'admin123'),
            ('mold_admin', 'mold123'),
            ('technician', 'tech123'),
            ('operator', 'op123')
        ]
        
        for username, password in test_users:
            print(f"\n测试用户: {username}")
            
            # 查询用户
            cursor.execute("""
                SELECT u.user_id, u.username, u.password_hash, u.full_name, r.role_name, u.is_active
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                WHERE u.username = %s AND u.is_active = true
            """, (username,))
            
            user = cursor.fetchone()
            
            if not user:
                print(f"  ❌ 用户 {username} 不存在或已禁用")
                continue
            
            # 验证密码
            stored_hash = user[2]
            input_hash = simple_hash_password(password)
            
            if stored_hash == input_hash:
                print(f"  ✅ 登录成功: {user[3]} ({user[4]})")
            else:
                print(f"  ❌ 密码错误")
                print(f"    存储哈希: {stored_hash[:20]}...")
                print(f"    输入哈希: {input_hash[:20]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")
        return False

def show_final_summary():
    """显示最终摘要"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("📊 最终用户摘要")
        print("="*60)
        
        cursor.execute("""
            SELECT u.user_id, u.username, u.full_name, r.role_name, u.email, u.is_active
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            ORDER BY u.user_id
        """)
        
        users = cursor.fetchall()
        
        print(f"\n系统中共有 {len(users)} 个用户:")
        print("-" * 60)
        
        for user in users:
            status = "启用" if user[5] else "禁用"
            print(f"ID: {user[0]}")
            print(f"  用户名: {user[1]}")
            print(f"  姓名: {user[2]}")
            print(f"  角色: {user[3]}")
            print(f"  邮箱: {user[4]}")
            print(f"  状态: {status}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取用户摘要失败: {e}")

def show_auth_py_update():
    """显示auth.py更新说明"""
    print("\n" + "="*60)
    print("📝 auth.py 更新说明")
    print("="*60)
    
    print("\n现在需要更新 app/utils/auth.py 文件:")
    print("\n1. 在文件顶部添加:")
    print("   import hashlib")
    
    print("\n2. 添加哈希函数:")
    print("""
def simple_hash_password(password):
    \"\"\"使用SHA256哈希密码\"\"\"
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
""")
    
    print("3. 更新 login_user 函数中的密码验证部分:")
    print("""
# 将现有的密码验证逻辑替换为:
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
    print("🔧 最终用户修复工具")
    print("="*60)
    
    # 1. 修复用户密码和角色
    if not fix_user_passwords_and_roles():
        return
    
    # 2. 测试所有登录
    if not test_all_logins():
        return
    
    # 3. 显示用户摘要
    show_final_summary()
    
    # 4. 显示auth.py更新说明
    show_auth_py_update()
    
    print("\n" + "="*60)
    print("🎉 所有修复完成!")
    print("="*60)
    
    print("\n🔑 测试账户 (用户名/密码):")
    print("   admin / admin123        (超级管理员)")
    print("   mold_admin / mold123    (模具库管理员)")
    print("   technician / tech123    (模具工)")
    print("   operator / op123        (冲压操作工)")
    
    print("\n📋 下一步:")
    print("   1. 按照上述说明更新 app/utils/auth.py")
    print("   2. 重启Streamlit: streamlit run app/main.py")
    print("   3. 使用任意账户登录测试")

if __name__ == "__main__":
    main()