-- 样例模具数据插入脚本
-- 在执行前请确保已经运行了 init_status_data.sql 初始化脚本

-- 插入样例模具数据
INSERT INTO molds (
    mold_code, mold_name, mold_drawing_number, mold_functional_type_id,
    supplier, manufacturing_date, acceptance_date, theoretical_lifespan_strokes,
    accumulated_strokes, maintenance_cycle_strokes, current_status_id, current_location_id,
    design_drawing_link, image_path, remarks, project_number, associated_equipment_number
) VALUES 
-- 落料模具
('LM001', 'Φ50钛平底杯-落料模', 'DWG-LM001-2024', 1, '模具工师傅', '2024-01-15', '2024-01-20', 50000, 12500, 5000, 1, 1, NULL, NULL, '主要用于Φ50钛合金平底杯的下料工序', 'PRJ-2024-001', 'PRESS-01'),

('LM002', 'Φ30钼圆片-落料模', 'DWG-LM002-2024', 1, '模具工师傅', '2024-02-10', '2024-02-15', 80000, 25000, 8000, 1, 2, NULL, NULL, '用于Φ30钼合金圆片的精密下料', 'PRJ-2024-002', 'PRESS-02'),

('LM003', 'Φ45锆异形杯-落料模', 'DWG-LM003-2024', 1, '模具工师傅', '2024-03-05', '2024-03-10', 60000, 8000, 6000, 2, 7, NULL, NULL, '异形杯产品专用落料模具，精度要求高', 'PRJ-2024-003', 'PRESS-01'),

-- 引申模具（一引）
('YS101', 'Φ50钛平底杯-一引模', 'DWG-YS101-2024', 2, '模具工师傅', '2024-01-20', '2024-01-25', 45000, 12000, 4500, 1, 1, NULL, NULL, '一道引申成型，控制壁厚均匀性', 'PRJ-2024-001', 'PRESS-03'),

('YS102', 'Φ45锆异形杯-一引模', 'DWG-YS102-2024', 2, '模具工师傅', '2024-03-10', '2024-03-15', 40000, 7500, 4000, 1, 2, NULL, NULL, '异形杯一引成型，注意压边圈配合', 'PRJ-2024-003', 'PRESS-03'),

-- 引申模具（二引）
('YS201', 'Φ50钛平底杯-二引模', 'DWG-YS201-2024', 3, '模具工师傅', '2024-02-01', '2024-02-05', 40000, 11800, 4000, 3, 7, NULL, NULL, '二道引申，达到最终深度要求', 'PRJ-2024-001', 'PRESS-04'),

('YS202', 'Φ45锆异形杯-二引模', 'DWG-YS202-2024', 3, '模具工师傅', '2024-03-20', '2024-03-25', 35000, 6500, 3500, 4, 7, NULL, NULL, '当前在维修中，压边圈需要更换', 'PRJ-2024-003', 'PRESS-04'),

-- 引申模具（三引）
('YS301', 'Φ50钛平底杯-三引模', 'DWG-YS301-2024', 4, '模具工师傅', '2024-02-10', '2024-02-15', 35000, 11200, 3500, 1, 3, NULL, NULL, '三道引申，形成最终杯型', 'PRJ-2024-001', 'PRESS-05'),

-- 切边模具
('QM001', 'Φ50钛平底杯-切边模', 'DWG-QM001-2024', 6, '模具工师傅', '2024-02-20', '2024-02-25', 60000, 12300, 6000, 1, 3, NULL, NULL, '最终切边成型，保证产品尺寸精度', 'PRJ-2024-001', 'PRESS-06'),

('QM002', 'Φ30钼圆片-切边模', 'DWG-QM002-2024', 6, '模具工师傅', '2024-02-25', '2024-03-01', 70000, 24800, 7000, 5, 2, NULL, NULL, '需要定期保养，下次保养还需200冲次', 'PRJ-2024-002', 'PRESS-06'),

-- 新项目模具
('LM004', 'Φ60铌合金深杯-落料模', 'DWG-LM004-2024', 1, '模具工师傅', '2024-04-01', '2024-04-05', 45000, 0, 4500, 1, 4, NULL, NULL, '新项目模具，尚未投入使用', 'PRJ-2024-004', 'PRESS-01'),

('YS103', 'Φ35钽异形件-一引模', 'DWG-YS103-2024', 2, '模具工师傅', '2024-04-10', '2024-04-15', 30000, 2500, 3000, 2, 8, NULL, NULL, '高精度钽合金成型，目前已借出使用', 'PRJ-2024-005', 'PRESS-07'),

-- 老旧模具
('LM005', 'Φ40铜合金圆片-落料模', 'DWG-LM005-2023', 1, '模具工师傅', '2023-08-15', '2023-08-20', 100000, 95000, 10000, 6, 7, NULL, NULL, '老旧模具，接近寿命极限，建议考虑报废', 'PRJ-2023-008', 'PRESS-02'),

('QM003', 'Φ55铁合金杯型-切边模', 'DWG-QM003-2023', 6, '模具工师傅', '2023-10-01', '2023-10-05', 80000, 78500, 8000, 7, 7, NULL, NULL, '正在进行定期保养，预计3天完成', 'PRJ-2023-010', 'PRESS-06'),

-- 特殊工艺模具
('LM006', 'Φ25钴合金精密件-落料模', 'DWG-LM006-2024', 1, '模具工师傅', '2024-05-01', '2024-05-05', 25000, 3200, 2500, 1, 5, NULL, NULL, '精密件专用，公差要求±0.01mm', 'PRJ-2024-006', 'PRESS-08')

ON CONFLICT (mold_code) DO NOTHING;

-- 插入模具部件数据（压边圈等关键部件）
INSERT INTO mold_parts (
    mold_id, part_code, part_name, part_category_id, material, supplier, 
    installation_date, lifespan_strokes, current_status_id, remarks
) VALUES 
-- LM001 的部件
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 'LM001-UP', 'LM001上模', 2, '工具钢T10A', '模具工师傅', '2024-01-15', 50000, 1, '上模部分，状态良好'),
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 'LM001-DOWN', 'LM001下模', 3, '工具钢T10A', '模具工师傅', '2024-01-15', 50000, 1, '下模部分，状态良好'),
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 'LM001-FRAME', 'LM001模架', 1, '钢材Q235', '模具工师傅', '2024-01-15', 100000, 1, '模架结构，承载能力强'),
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 'LM001-RING', 'LM001压边圈', 5, '硬质合金', '模具工师傅', '2024-01-15', 30000, 1, 'Φ50专用压边圈，控制材料流动'),

-- YS101 的部件（包含重要的压边圈）
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 'YS101-UP', 'YS101上模', 2, '工具钢T10A', '模具工师傅', '2024-01-20', 45000, 1, '引申上模，表面镀铬'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 'YS101-DOWN', 'YS101下模', 3, '工具钢T10A', '模具工师傅', '2024-01-20', 45000, 1, '引申下模，表面镀铬'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 'YS101-CORE', 'YS101芯子', 4, '硬质合金', '模具工师傅', '2024-01-20', 45000, 1, '成型芯子，精度要求高'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 'YS101-RING', 'YS101压边圈', 5, '硬质合金', '模具工师傅', '2024-01-20', 25000, 1, '引申专用压边圈，防止起皱'),

-- YS202 的部件（维修中的模具）
((SELECT mold_id FROM molds WHERE mold_code = 'YS202'), 'YS202-UP', 'YS202上模', 2, '工具钢T10A', '模具工师傅', '2024-03-20', 35000, 1, '上模状态正常'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS202'), 'YS202-DOWN', 'YS202下模', 3, '工具钢T10A', '模具工师傅', '2024-03-20', 35000, 1, '下模状态正常'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS202'), 'YS202-RING-OLD', 'YS202压边圈(旧)', 5, '硬质合金', '模具工师傅', '2024-03-20', 35000, 4, '压边圈磨损严重，需要更换'),

-- QM002 的部件（需要保养的模具）
((SELECT mold_id FROM molds WHERE mold_code = 'QM002'), 'QM002-UP', 'QM002上模', 2, '工具钢D2', '模具工师傅', '2024-02-25', 70000, 6, '需要保养，表面有轻微磨损'),
((SELECT mold_id FROM molds WHERE mold_code = 'QM002'), 'QM002-DOWN', 'QM002下模', 3, '工具钢D2', '模具工师傅', '2024-02-25', 70000, 6, '需要保养，刃口需要修磨'),
((SELECT mold_id FROM molds WHERE mold_code = 'QM002'), 'QM002-RING', 'QM002压边圈', 5, '硬质合金', '模具工师傅', '2024-02-25', 50000, 1, '压边圈状态良好')

ON CONFLICT (part_code) DO NOTHING;

-- 插入一些样例借用记录
INSERT INTO mold_loan_records (
    mold_id, applicant_id, application_timestamp, approver_id, approval_timestamp,
    loan_out_timestamp, expected_return_timestamp, actual_return_timestamp,
    loan_status_id, destination_equipment, remarks
) VALUES 
-- 已完成的借用记录
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 4, '2024-01-25 08:30:00', 2, '2024-01-25 09:00:00', '2024-01-25 10:00:00', '2024-01-27 18:00:00', '2024-01-27 16:30:00', 4, 'PRESS-01', '生产Φ50钛杯1000只，质量良好'),

((SELECT mold_id FROM molds WHERE mold_code = 'QM001'), 4, '2024-01-28 09:00:00', 2, '2024-01-28 09:15:00', '2024-01-28 10:30:00', '2024-01-30 18:00:00', '2024-01-30 17:45:00', 4, 'PRESS-06', '切边工序，完成800只产品'),

-- 当前借出中的记录
((SELECT mold_id FROM molds WHERE mold_code = 'YS103'), 4, '2024-04-16 10:00:00', 2, '2024-04-16 10:30:00', '2024-04-16 14:00:00', '2024-04-18 18:00:00', NULL, 3, 'PRESS-07', '生产钽合金异形件，预计2天完成'),

-- 待审批的记录
((SELECT mold_id FROM molds WHERE mold_code = 'LM002'), 4, '2024-04-17 15:30:00', NULL, NULL, NULL, '2024-04-19 18:00:00', NULL, 1, 'PRESS-02', '紧急生产任务，需要尽快审批')

ON CONFLICT DO NOTHING;

-- 插入一些使用记录
INSERT INTO mold_usage_records (
    mold_id, operator_id, equipment_id, production_order_number, product_id_produced,
    start_timestamp, end_timestamp, strokes_this_session, produced_quantity, qualified_quantity, notes
) VALUES 
-- LM001 的使用记录
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 4, 'PRESS-01', 'PO-2024-001', NULL, '2024-01-25 10:00:00', '2024-01-25 18:00:00', 1000, 1000, 995, '生产顺利，5只产品尺寸略有偏差'),
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 4, 'PRESS-01', 'PO-2024-002', NULL, '2024-01-26 08:00:00', '2024-01-26 17:30:00', 1200, 1200, 1198, '生产正常，质量稳定'),
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 4, 'PRESS-01', 'PO-2024-003', NULL, '2024-02-15 09:00:00', '2024-02-15 17:00:00', 800, 800, 800, '完美生产，零缺陷'),

-- LM002 的使用记录
((SELECT mold_id FROM molds WHERE mold_code = 'LM002'), 4, 'PRESS-02', 'PO-2024-005', NULL, '2024-02-20 08:30:00', '2024-02-22 17:30:00', 2500, 2500, 2490, '3天连续生产，模具状态良好'),

-- YS101 的使用记录
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 4, 'PRESS-03', 'PO-2024-001', NULL, '2024-01-26 08:00:00', '2024-01-26 18:00:00', 1000, 1000, 999, '引申工序顺利，1只产品开裂'),
((SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 4, 'PRESS-03', 'PO-2024-002', NULL, '2024-01-27 08:00:00', '2024-01-27 17:30:00', 1200, 1200, 1200, '引申质量优秀，零缺陷'),

-- QM001 的使用记录
((SELECT mold_id FROM molds WHERE mold_code = 'QM001'), 4, 'PRESS-06', 'PO-2024-001', NULL, '2024-01-29 09:00:00', '2024-01-29 17:00:00', 800, 800, 798, '切边精度高，2只产品毛刺略大')

ON CONFLICT DO NOTHING;

-- 插入维修保养记录
INSERT INTO mold_maintenance_logs (
    mold_id, part_id, maintenance_type_id, problem_description, actions_taken,
    maintenance_start_timestamp, maintenance_end_timestamp, maintained_by_id,
    replaced_parts_info, maintenance_cost, result_status_id, notes
) VALUES 
-- YS202 的维修记录（当前维修中）
((SELECT mold_id FROM molds WHERE mold_code = 'YS202'), NULL, 3, '压边圈磨损严重，影响成型质量', '更换新的压边圈，重新调试间隙', '2024-04-15 08:00:00', NULL, 3, '{"parts":[{"name":"压边圈","code":"YS202-RING-NEW","quantity":1}]}', 1200.00, 4, '等待新压边圈到货，预计明天完成'),

-- LM001 的保养记录
((SELECT mold_id FROM molds WHERE mold_code = 'LM001'), NULL, 2, '达到保养周期，需要定期维护', '清洁模具表面，检查各部件磨损情况，重新润滑', '2024-03-01 08:00:00', '2024-03-01 17:00:00', 3, NULL, 200.00, 2, '定期保养完成，模具状态良好'),

-- QM002 的保养记录（正在保养中）
((SELECT mold_id FROM molds WHERE mold_code = 'QM002'), NULL, 2, '接近保养周期，切边刃口有轻微磨损', '修磨切边刃口，调整间隙，全面清洁保养', '2024-04-16 08:00:00', NULL, 3, NULL, 300.00, 1, '正在进行保养，预计今天下午完成'),

-- LM005 的维修记录（老旧模具）
((SELECT mold_id FROM molds WHERE mold_code = 'LM005'), NULL, 3, '模具老化，多处磨损严重', '修复主要磨损部位，但效果有限', '2024-03-20 08:00:00', '2024-03-22 17:00:00', 3, NULL, 800.00, 2, '修复完成但建议考虑报废更换')

ON CONFLICT DO NOTHING;

-- 插入产品信息（如果需要）
INSERT INTO products (
    product_code, product_name, product_drawing_number, product_type_id, material_id, description
) VALUES 
('PROD-001', 'Φ50钛合金平底杯', 'PROD-DWG-001', 1, 1, '标准Φ50钛合金平底杯，壁厚0.5mm'),
('PROD-002', 'Φ30钼合金圆片', 'PROD-DWG-002', 3, 2, 'Φ30钼合金圆片，厚度1.0mm'),
('PROD-003', 'Φ45锆合金异形杯', 'PROD-DWG-003', 2, 3, '异形杯产品，形状特殊，精度要求高'),
('PROD-004', 'Φ35钽合金异形件', 'PROD-DWG-004', 2, 5, '高精度钽合金异形件'),
('PROD-005', 'Φ25钴合金精密件', 'PROD-DWG-005', 2, 6, '精密钴合金件，公差±0.01mm')

ON CONFLICT (product_code) DO NOTHING;

-- 插入产品工艺流程关联
INSERT INTO product_process_flow (
    product_id, mold_id, sequence_order, process_step_name, remarks
) VALUES 
-- Φ50钛合金平底杯的工艺流程
((SELECT product_id FROM products WHERE product_code = 'PROD-001'), (SELECT mold_id FROM molds WHERE mold_code = 'LM001'), 1, '落料', '下料工序'),
((SELECT product_id FROM products WHERE product_code = 'PROD-001'), (SELECT mold_id FROM molds WHERE mold_code = 'YS101'), 2, '一引', '第一次拉伸'),
((SELECT product_id FROM products WHERE product_code = 'PROD-001'), (SELECT mold_id FROM molds WHERE mold_code = 'YS201'), 3, '二引', '第二次拉伸'),
((SELECT product_id FROM products WHERE product_code = 'PROD-001'), (SELECT mold_id FROM molds WHERE mold_code = 'YS301'), 4, '三引', '第三次拉伸成型'),
((SELECT product_id FROM products WHERE product_code = 'PROD-001'), (SELECT mold_id FROM molds WHERE mold_code = 'QM001'), 5, '切边', '最终切边成型'),

-- Φ30钼合金圆片的工艺流程（只需落料和切边）
((SELECT product_id FROM products WHERE product_code = 'PROD-002'), (SELECT mold_id FROM molds WHERE mold_code = 'LM002'), 1, '落料', '下料工序'),
((SELECT product_id FROM products WHERE product_code = 'PROD-002'), (SELECT mold_id FROM molds WHERE mold_code = 'QM002'), 2, '切边', '精密切边'),

-- Φ45锆合金异形杯的工艺流程
((SELECT product_id FROM products WHERE product_code = 'PROD-003'), (SELECT mold_id FROM molds WHERE mold_code = 'LM003'), 1, '落料', '异形件下料'),
((SELECT product_id FROM products WHERE product_code = 'PROD-003'), (SELECT mold_id FROM molds WHERE mold_code = 'YS102'), 2, '一引', '异形一引成型'),
((SELECT product_id FROM products WHERE product_code = 'PROD-003'), (SELECT mold_id FROM molds WHERE mold_code = 'YS202'), 3, '二引', '异形二引成型')

ON CONFLICT (product_id, sequence_order) DO NOTHING;

-- 更新一些模具的累计冲次（应该等于各次使用记录的总和）
UPDATE molds SET accumulated_strokes = (
    SELECT COALESCE(SUM(strokes_this_session), 0) 
    FROM mold_usage_records 
    WHERE mold_usage_records.mold_id = molds.mold_id
) WHERE mold_code IN ('LM001', 'LM002', 'YS101', 'QM001');

-- 查询验证数据
SELECT 'Data Summary' as info, COUNT(*) as count FROM molds
UNION ALL
SELECT 'Mold Parts', COUNT(*) FROM mold_parts  
UNION ALL
SELECT 'Loan Records', COUNT(*) FROM mold_loan_records
UNION ALL
SELECT 'Usage Records', COUNT(*) FROM mold_usage_records
UNION ALL
SELECT 'Maintenance Logs', COUNT(*) FROM mold_maintenance_logs
UNION ALL
SELECT 'Products', COUNT(*) FROM products
UNION ALL
SELECT 'Process Flow', COUNT(*) FROM product_process_flow;