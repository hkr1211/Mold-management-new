# diagnosis.py - 创建这个文件用于诊断
import streamlit as st
import psycopg2
import psycopg2.extras
import os

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mold_management'),
    'user': os.getenv('DB_USER', 'mold_user'),
    'password': os.getenv('DB_PASSWORD', 'mold_password_123'),
    'port': os.getenv('DB_PORT', '5432')
}

def main():
    st.title("🔍 数据库结构诊断工具")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        st.success("✅ 数据库连接成功")
        
        # 检查所有表
        st.subheader("📋 检查所有表")
        cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        table_names = [t['table_name'] for t in tables]
        
        st.write(f"找到 {len(tables)} 个表:")
        for table in table_names:
            st.write(f"- {table}")
        
        # 重点检查molds表
        if 'molds' in table_names:
            st.subheader("🔧 molds表详细结构")
            
            cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'molds' 
            ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            
            if columns:
                st.write("**字段详情:**")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                    default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
                    
                    st.write(f"- **{col['column_name']}**: {col['data_type']}{max_len} {nullable} {default}")
                
                # 显示数据样本
                st.subheader("📊 molds表数据样本")
                cursor.execute("SELECT COUNT(*) FROM molds")
                count = cursor.fetchone()['count']
                st.write(f"总记录数: {count}")
                
                if count > 0:
                    cursor.execute("SELECT * FROM molds LIMIT 3")
                    samples = cursor.fetchall()
                    
                    st.write("**前3条记录:**")
                    for i, row in enumerate(samples, 1):
                        st.write(f"记录 {i}:")
                        for key, value in row.items():
                            st.write(f"  {key}: {value}")
                        st.write("---")
                else:
                    st.warning("表中无数据")
            else:
                st.error("无法获取molds表结构")
        else:
            st.error("❌ molds表不存在!")
        
        # 检查关联表
        st.subheader("🔗 检查关联表")
        related_tables = ['mold_statuses', 'storage_locations', 'mold_functional_types']
        
        for table in related_tables:
            if table in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()['count']
                st.write(f"✅ {table}: {count} 条记录")
                
                # 显示几条样本数据
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                samples = cursor.fetchall()
                for sample in samples:
                    st.write(f"  - {dict(sample)}")
            else:
                st.write(f"❌ {table}: 表不存在")
        
        conn.close()
        
        # 提供建议
        st.subheader("💡 建议")
        
        if 'molds' not in table_names:
            st.error("**严重问题**: molds表不存在，需要运行数据库初始化脚本")
            st.code("python setup_database.py")
        else:
            columns_list = [col['column_name'] for col in columns]
            
            missing_basic = []
            basic_fields = ['mold_id', 'mold_code', 'mold_name']
            for field in basic_fields:
                if field not in columns_list:
                    missing_basic.append(field)
            
            if missing_basic:
                st.error(f"缺少基本字段: {', '.join(missing_basic)}")
            else:
                st.success("✅ 基本字段完整")
                
                # 检查可选字段
                optional_fields = ['supplier', 'theoretical_lifespan_strokes', 'accumulated_strokes']
                missing_optional = [f for f in optional_fields if f not in columns_list]
                
                if missing_optional:
                    st.warning(f"可选字段缺失: {', '.join(missing_optional)}")
                    st.info("系统会自动适配，但建议添加这些字段以获得完整功能")
                else:
                    st.success("✅ 所有推荐字段都存在")
    
    except Exception as e:
        st.error(f"❌ 诊断失败: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()