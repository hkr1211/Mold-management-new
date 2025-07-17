#!/usr/bin/env python3
"""
插入样例模具数据的脚本
"""

import psycopg2
import os
import sys
from pathlib import Path

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mold_management'),
    'user': os.getenv('DB_USER', 'mold_user'),
    'password': os.getenv('DB_PASSWORD', 'mold_password_123'),
    'port': os.getenv('DB_PORT', '5432')
}

def insert_sample_data():
    """插入样例数据"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("开始插入样例模具数据...")
        
        # 读取并执行样例数据SQL文件
        sql_file = Path(__file__).parent / "sample_mold_data.sql"
        
        if sql_file.exists():
            print("从SQL文件插入数据...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            cursor.execute(sql_content)
        else:
            print("SQL文件不存在，直接插入数据...")
            # 直接在代码中定义样例数据
            insert_direct_sample_data(cursor)
        
        conn.commit()
        print("✓ 样例数据插入成功！")
        
        # 验证插入结果
        print("\n数据统计：")
        verification_queries = [
            ("模具总数", "SELECT COUNT(*) FROM molds"),
            ("模具部件总数", "SELECT COUNT(*) FROM mold_parts"),
            ("借用记录总数", "SELECT COUNT(*) FROM mold_loan_records"),
            ("使用记录总数", "SELECT COUNT(*) FROM mold_usage_records"),
            ("维修记录总数", "SELECT COUNT(*) FROM mold_maintenance_logs"),
            ("产品总数", "SELECT COUNT(*) FROM products"),
            ("工艺流程总数", "SELECT COUNT(*) FROM product_process_flow")
        ]
        
        for desc, query in verification_queries:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  {desc}: {count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"插入样例数据失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def insert_direct_sample_data(cursor):
    """直接插入样例数据（不依赖外部SQL文件）"""
    
    # 插入样例模具数据
    mold_data = [
        ('LM001', 'Φ50钛平底杯-落料模', 'DWG-LM001-2024', 1, '模具工师傅', '2024-01-15', '2024-01-20', 50000, 12500, 5000, 1, 1, '主要用于Φ50钛合金平底杯的下料工序', 'PRJ-2024-001', 'PRESS-01'),
        ('LM002', 'Φ30钼圆片-落料模', 'DWG-LM002-2024', 1, '模具工师傅', '2024-02-10', '2024-02-15', 80000, 25000, 8000, 1, 2, '用于Φ30钼合金圆片的精密下料', 'PRJ-2024-002', 'PRESS-02'),
        ('LM003', 'Φ45锆异形杯-落料模', 'DWG-LM003-2024', 1, '模具工师傅', '2024-03-05', '2024-03-10', 60000, 8000, 6000, 2, 7, '异形杯产品专用落料模具，精度要求高', 'PRJ-2024-003', 'PRESS-01'),
        ('YS101', 'Φ50钛平底杯-一引模', 'DWG-YS101-2024', 2, '模具工师傅', '2024-01-20', '2024-01-25', 45000, 12000, 4500, 1, 1, '一道引申成型，控制壁厚均匀性', 'PRJ-2024-001', 'PRESS-03'),
        ('YS102', 'Φ45锆异形杯-一引模', 'DWG-YS102-2024', 2, '模具工师傅', '2024-03-10', '2024-03-15', 40000, 7500, 4000, 1, 2, '异形杯一引成型，注意压边圈配合', 'PRJ-2024-003', 'PRESS-03'),
        ('YS201', 'Φ50钛平底杯-二引模', 'DWG-YS201-2024', 3, '模具工师傅', '2024-02-01', '2024-02-05', 40000, 11800, 4000, 3, 7, '二道引申，达到最终深度要求', 'PRJ-2024-001', 'PRESS-04'),
        ('YS202', 'Φ45锆异形杯-二引模', 'DWG-YS202-2024', 3, '模具工师傅', '2024-03-20', '2024-03-25', 35000, 6500, 3500, 4, 7, '当前在维修中，压边圈需要更换', 'PRJ-2024-003', 'PRESS-04'),
        ('YS301', 'Φ50钛平底杯-三引模', 'DWG-YS301-2024', 4, '模具工师傅', '2024-02-10', '2024-02-15', 35000, 11200, 3500, 1, 3, '三道引申，形成最终杯型', 'PRJ-2024-001', 'PRESS-05'),
        ('QM001', 'Φ50钛平底杯-切边模', 'DWG-QM001-2024', 6, '模具工师傅', '2024-02-20', '2024-02-25', 60000, 12300, 6000, 1, 3, '最终切边成型，保证产品尺寸精度', 'PRJ-2024-001', 'PRESS-06'),
        ('QM002', 'Φ30钼圆片-切边模', 'DWG-QM002-2024', 6, '模具工师傅', '2024-02-25', '2024-03-01', 70000, 24800, 7000, 5, 2, '需要定期保养，下次保养还需200冲次', 'PRJ-2024-002', 'PRESS-06'),
        ('LM004', 'Φ60铌合金深杯-落料模', 'DWG-LM004-2024', 1, '模具工师傅', '2024-04-01', '2024-04-05', 45000, 0, 4500, 1, 4, '新项目模具，尚未投入使用', 'PRJ-2024-004', 'PRESS-01'),
        ('YS103', 'Φ35钽异形件-一引模', 'DWG-YS103-2024', 2, '模具工师傅', '2024-04-10', '2024-04-15', 30000, 2500, 3000, 2, 8, '高精度钽合金成型，目前已借出使用', 'PRJ-2024-005', 'PRESS-07'),
        ('LM005', 'Φ40铜合金圆片-落料模', 'DWG-LM005-2023', 1, '模具工师傅', '2023-08-15', '2023-08-20', 100000, 95000, 10000, 6, 7, '老旧模具，接近寿命极限，建议考虑报废', 'PRJ-2023-008', 'PRESS-02'),
        ('QM003', 'Φ55铁合金杯型-切边模', 'DWG-QM003-2023', 6, '模具工师傅', '2023-10-01', '2023-10-05', 80000, 78500, 8000, 7, 7, '正在进行定期保养，预计3天完成', 'PRJ-2023-010', 'PRESS-06'),
        ('LM006', 'Φ25钴合金精密件-落料模', 'DWG-LM006-2024', 1, '模具工师傅', '2024-05-01', '2024-05-05', 25000, 3200, 2500, 1, 5, '精密件专用，公差要求±0.01mm', 'PRJ-2024-006', 'PRESS-08')
    ]
    
    insert_mold_query = """
    INSERT INTO molds (
        mold_code, mold_name, mold_drawing_number, mold_functional_type_id,
        supplier, manufacturing_date, acceptance_date, theoretical_lifespan_strokes,
        accumulated_strokes, maintenance_cycle_strokes, current_status_id, current_location_id,
        remarks, project_number, associated_equipment_number
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (mold_code) DO NOTHING
    """
    
    cursor.executemany(insert_mold_query, mold_data)
    print("✓ 插入模具数据")
    
    # 插入样例产品数据
    product_data = [
        ('PROD-001', 'Φ50钛合金平底杯', 'PROD-DWG-001', 1, 1, '标准Φ50钛合金平底杯，壁厚0.5mm'),
        ('PROD-002', 'Φ30钼合金圆片', 'PROD-DWG-002', 3, 2, 'Φ30钼合金圆片，厚度1.0mm'),
        ('PROD-003', 'Φ45锆合金异形杯', 'PROD-DWG-003', 2, 3, '异形杯产品，形状特殊，精度要求高'),
        ('PROD-004', 'Φ35钽合金异形件', 'PROD-DWG-004', 2, 5, '高精度钽合金异形件'),
        ('PROD-005', 'Φ25钴合金精密件', 'PROD-DWG-005', 2, 6, '精密钴合金件，公差±0.01mm')
    ]
    
    insert_product_query = """
    INSERT INTO products (
        product_code, product_name, product_drawing_number, product_type_id, material_id, description
    ) VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (product_code) DO NOTHING
    """
    
    cursor.executemany(insert_product_query, product_data)
    print("✓ 插入产品数据")
    
    # 插入模具部件数据（使用子查询获取mold_id）
    part_insert_queries = [
        # LM001 的部件
        "INSERT INTO mold_parts (mold_id, part_code, part_name, part_category_id, material, supplier, installation_date, lifespan_strokes, current_status_id, remarks) SELECT mold_id, 'LM001-UP', 'LM001上模', 2, '工具钢T10A', '模具工师傅', '2024-01-15', 50000, 1, '上模部分，状态良好' FROM molds WHERE mold_code = 'LM001' ON CONFLICT (part_code) DO NOTHING",
        "INSERT INTO mold_parts (mold_id, part_code, part_name, part_category_id, material, supplier, installation_date, lifespan_strokes, current_status_id, remarks) SELECT mold_id, 'LM001-DOWN', 'LM001下模', 3, '工具钢T10A', '模具工师傅', '2024-01-15', 50000, 1, '下模部分，状态良好' FROM molds WHERE mold_code = 'LM001' ON CONFLICT (part_code) DO NOTHING",
        "INSERT INTO mold_parts (mold_id, part_code, part_name, part_category_id, material, supplier, installation_date, lifespan_strokes, current_status_id, remarks) SELECT mold_id, 'LM001-RING', 'LM001压边圈', 5, '硬质合金', '模具工师傅', '2024-01-15', 30000, 1, 'Φ50专用压边圈，控制材料流动' FROM molds WHERE mold_code = 'LM001' ON CONFLICT (part_code) DO NOTHING",
        
        # YS101 的部件
        "INSERT INTO mold_parts (mold_id, part_code, part_name, part_category_id, material, supplier, installation_date, lifespan_strokes, current_status_id, remarks) SELECT mold_id, 'YS101-UP', 'YS101上模', 2, '工具钢T10A', '模具工师傅', '2024-01-20', 45000, 1, '引申上模，表面镀铬' FROM molds WHERE mold_code = 'YS101' ON CONFLICT (part_code) DO NOTHING",
        "INSERT INTO mold_parts (mold_id, part_code, part_name, part_category_id, material, supplier, installation_date, lifespan_strokes, current_status_id, remarks) SELECT mold_id, 'YS101-RING', 'YS101压边圈', 5, '硬质合金', '模具工师傅', '2024-01-20', 25000, 1, '引申专用压边圈，防止起皱' FROM molds WHERE mold_code = 'YS101' ON CONFLICT (part_code) DO NOTHING",
    ]
    
    for query in part_insert_queries:
        cursor.execute(query)
    print("✓ 插入模具部件数据")
    
    # 插入借用记录
    loan_insert_queries = [
        "INSERT INTO mold_loan_records (mold_id, applicant_id, application_timestamp, approver_id, approval_timestamp, loan_out_timestamp, expected_return_timestamp, actual_return_timestamp, loan_status_id, destination_equipment, remarks) SELECT mold_id, 4, '2024-01-25 08:30:00', 2, '2024-01-25 09:00:00', '2024-01-25 10:00:00', '2024-01-27 18:00:00', '2024-01-27 16:30:00', 4, 'PRESS-01', '生产Φ50钛杯1000只，质量良好' FROM molds WHERE mold_code = 'LM001'",
        "INSERT INTO mold_loan_records (mold_id, applicant_id, application_timestamp, approver_id, approval_timestamp, loan_out_timestamp, expected_return_timestamp, loan_status_id, destination_equipment, remarks) SELECT mold_id, 4, '2024-04-16 10:00:00', 2, '2024-04-16 10:30:00', '2024-04-16 14:00:00', '2024-04-18 18:00:00', 3, 'PRESS-07', '生产钽合金异形件，预计2天完成' FROM molds WHERE mold_code = 'YS103'",
    ]
    
    for query in loan_insert_queries:
        cursor.execute(query)
    print("✓ 插入借用记录")
    
    # 插入使用记录
    usage_insert_queries = [
        "INSERT INTO mold_usage_records (mold_id, operator_id, equipment_id, production_order_number, start_timestamp, end_timestamp, strokes_this_session, produced_quantity, qualified_quantity, notes) SELECT mold_id, 4, 'PRESS-01', 'PO-2024-001', '2024-01-25 10:00:00', '2024-01-25 18:00:00', 1000, 1000, 995, '生产顺利，5只产品尺寸略有偏差' FROM molds WHERE mold_code = 'LM001'",
        "INSERT INTO mold_usage_records (mold_id, operator_id, equipment_id, production_order_number, start_timestamp, end_timestamp, strokes_this_session, produced_quantity, qualified_quantity, notes) SELECT mold_id, 4, 'PRESS-01', 'PO-2024-002', '2024-01-26 08:00:00', '2024-01-26 17:30:00', 1200, 1200, 1198, '生产正常，质量稳定' FROM molds WHERE mold_code = 'LM001'",
        "INSERT INTO mold_usage_records (mold_id, operator_id, equipment_id, production_order_number, start_timestamp, end_timestamp, strokes_this_session, produced_quantity, qualified_quantity, notes) SELECT mold_id, 4, 'PRESS-02', 'PO-2024-005', '2024-02-20 08:30:00', '2024-02-22 17:30:00', 2500, 2500, 2490, '3天连续生产，模具状态良好' FROM molds WHERE mold_code = 'LM002'",
    ]
    
    for query in usage_insert_queries:
        cursor.execute(query)
    print("✓ 插入使用记录")
    
    # 插入维修记录
    maintenance_insert_queries = [
        "INSERT INTO mold_maintenance_logs (mold_id, maintenance_type_id, problem_description, actions_taken, maintenance_start_timestamp, maintenance_end_timestamp, maintained_by_id, maintenance_cost, result_status_id, notes) SELECT mold_id, 3, '压边圈磨损严重，影响成型质量', '更换新的压边圈，重新调试间隙', '2024-04-15 08:00:00', NULL, 3, 1200.00, 4, '等待新压边圈到货，预计明天完成' FROM molds WHERE mold_code = 'YS202'",
        "INSERT INTO mold_maintenance_logs (mold_id, maintenance_type_id, problem_description, actions_taken, maintenance_start_timestamp, maintenance_end_timestamp, maintained_by_id, maintenance_cost, result_status_id, notes) SELECT mold_id, 2, '达到保养周期，需要定期维护', '清洁模具表面，检查各部件磨损情况，重新润滑', '2024-03-01 08:00:00', '2024-03-01 17:00:00', 3, 200.00, 2, '定期保养完成，模具状态良好' FROM molds WHERE mold_code = 'LM001'",
    ]
    
    for query in maintenance_insert_queries:
        cursor.execute(query)
    print("✓ 插入维修记录")

def main():
    """主函数"""
    print("=== 蕴杰金属冲压模具管理系统 - 样例数据插入 ===\n")
    
    # 测试数据库连接
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("请检查数据库配置和连接状态")
        return False
    
    # 插入样例数据
    if insert_sample_data():
        print("\n=== 样例数据插入完成! ===")
        print("\n现在您可以启动系统并看到以下样例数据：")
        print("- 15个不同类型的模具（落料、引申、切边）")
        print("- 涵盖不同状态：闲置、使用中、维修中、保养中、已借出")
        print("- 包含模具部件信息（压边圈等）")
        print("- 借用记录、使用记录、维修记录")
        print("- 产品信息和工艺流程")
        print("\n登录系统后可以在模具管理页面查看这些数据")
        return True
    else:
        print("\n=== 样例数据插入失败! ===")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)