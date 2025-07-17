-- 基础数据插入

-- 插入模具功能类型
INSERT INTO mold_functional_types (type_name, type_code, description, sort_order) VALUES
('落料模', 'LUOLIAO', '用于金属片材的落料成型', 1),
('一引模', 'YIYIN', '第一次拉伸成型模具', 2),
('二引模', 'ERYIN', '第二次拉伸成型模具', 3),
('三引模', 'SANYIN', '第三次拉伸成型模具', 4),
('四引模', 'SIYIN', '第四次拉伸成型模具', 5),
('切边模', 'QIEBIAN', '用于产品切边整形', 6)
ON CONFLICT (type_name) DO NOTHING;

-- 插入模具状态
INSERT INTO mold_statuses (status_name, status_code, status_color, is_available, description, sort_order) VALUES
('闲置', 'IDLE', '#28a745', TRUE, '模具空闲可用状态', 1),
('使用中', 'IN_USE', '#007bff', FALSE, '模具正在生产中', 2),
('已借出', 'BORROWED', '#ffc107', FALSE, '模具已被借用', 3),
('维修中', 'REPAIRING', '#dc3545', FALSE, '模具正在维修', 4),
('保养中', 'MAINTENANCE', '#fd7e14', FALSE, '模具正在保养', 5),
('待维修', 'NEED_REPAIR', '#e83e8c', FALSE, '模具需要维修', 6),
('待保养', 'NEED_MAINTENANCE', '#6f42c1', FALSE, '模具需要保养', 7),
('报废', 'SCRAPPED', '#6c757d', FALSE, '模具已报废', 8)
ON CONFLICT (status_name) DO NOTHING;

-- 插入存放位置
INSERT INTO storage_locations (location_name, location_code, area, rack_number, level_number, description) VALUES
('A区-01架-1层', 'A01-L1', 'A区', '01', '1', 'A区第1号货架第1层'),
('A区-01架-2层', 'A01-L2', 'A区', '01', '2', 'A区第1号货架第2层'),
('A区-02架-1层', 'A02-L1', 'A区', '02', '1', 'A区第2号货架第1层'),
('A区-02架-2层', 'A02-L2', 'A区', '02', '2', 'A区第2号货架第2层'),
('B区-01架-1层', 'B01-L1', 'B区', '01', '1', 'B区第1号货架第1层'),
('B区-01架-2层', 'B01-L2', 'B区', '01', '2', 'B区第1号货架第2层'),
('维修车间', 'REPAIR', '维修区', 'R01', '1', '模具维修车间'),
('生产车间', 'PRODUCTION', '生产区', 'P01', '1', '生产现场')
ON CONFLICT (location_name) DO NOTHING;

-- 插入金属材料
INSERT INTO materials (material_name, material_code, density, description) VALUES
('钛', 'TI', 4.506, '钛金属材料，强度高，耐腐蚀'),
('钼', 'MO', 10.280, '钼金属材料，高熔点，耐高温'),
('锆', 'ZR', 6.520, '锆金属材料，耐腐蚀性好'),
('铌', 'NB', 8.570, '铌金属材料，超导材料'),
('钽', 'TA', 16.650, '钽金属材料，化学性质稳定'),
('钴', 'CO', 8.900, '钴金属材料，磁性材料'),
('铜', 'CU', 8.960, '铜金属材料，导电性好'),
('铁', 'FE', 7.874, '铁金属材料，应用广泛')
ON CONFLICT (material_name) DO NOTHING;

-- 插入示例模具数据
INSERT INTO molds (
    mold_code, mold_name, mold_functional_type_id, current_status_id, current_location_id,
    theoretical_lifespan_strokes, maintenance_cycle_strokes, manufacturer, 
    has_coating, priority_level, remarks
) VALUES
('MD001', 'Φ50钛平底杯落料模', 1, 1, 1, 100000, 5000, '模具工张师傅', TRUE, 4, '高精度落料模，适用于钛材加工'),
('MD002', 'Φ50钛平底杯一引模', 2, 1, 2, 80000, 4000, '模具工张师傅', TRUE, 4, '第一次拉伸成型模具'),
('MD003', 'Φ30钼圆片落料模', 1, 2, 8, 120000, 6000, '模具工李师傅', FALSE, 3, '钼材圆片落料专用模具')
ON CONFLICT (mold_code) DO NOTHING;

-- 创建视图
CREATE OR REPLACE VIEW v_mold_summary AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    mft.type_name as mold_type,
    ms.status_name as current_status,
    ms.status_color,
    sl.location_name as current_location,
    m.accumulated_strokes,
    m.theoretical_lifespan_strokes,
    CASE 
        WHEN m.theoretical_lifespan_strokes > 0 THEN 
            ROUND((m.accumulated_strokes::DECIMAL / m.theoretical_lifespan_strokes * 100), 2)
        ELSE 0 
    END as usage_percentage,
    m.has_coating,
    m.is_precision_mold,
    m.priority_level,
    m.entry_date,
    m.created_at
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id;
