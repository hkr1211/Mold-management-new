-- 模具管理系统 - 核心表结构
-- 创建时间: 2025-05-26
-- 说明: 专注于模具管理的核心数据结构

-- 1. 模具功能类型表
CREATE TABLE IF NOT EXISTS mold_functional_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    type_code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入模具功能类型基础数据
INSERT INTO mold_functional_types (type_name, type_code, description, sort_order) VALUES
('落料模', 'LUOLIAO', '用于金属片材的落料成型', 1),
('一引模', 'YIYIN', '第一次拉伸成型模具', 2),
('二引模', 'ERYIN', '第二次拉伸成型模具', 3),
('三引模', 'SANYIN', '第三次拉伸成型模具', 4),
('四引模', 'SIYIN', '第四次拉伸成型模具', 5),
('切边模', 'QIEBIAN', '用于产品切边整形', 6)
ON CONFLICT (type_name) DO NOTHING;

-- 2. 模具状态字典表
CREATE TABLE IF NOT EXISTS mold_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    status_code VARCHAR(20) UNIQUE NOT NULL,
    status_color VARCHAR(10) DEFAULT '#666666',
    description TEXT,
    is_available BOOLEAN DEFAULT TRUE, -- 是否可借用
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入模具状态基础数据
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

-- 3. 存放位置字典表
CREATE TABLE IF NOT EXISTS storage_locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    location_code VARCHAR(20) UNIQUE NOT NULL,
    area VARCHAR(50), -- 区域 (A区、B区等)
    rack_number VARCHAR(20), -- 货架号
    level_number VARCHAR(10), -- 层号
    capacity INTEGER DEFAULT 0, -- 容量
    current_count INTEGER DEFAULT 0, -- 当前存放数量
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入存放位置基础数据
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

-- 4. 金属材料表
CREATE TABLE IF NOT EXISTS materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(100) UNIQUE NOT NULL,
    material_code VARCHAR(20) UNIQUE NOT NULL,
    density DECIMAL(8,4), -- 密度 g/cm³
    hardness VARCHAR(50), -- 硬度
    melting_point INTEGER, -- 熔点 ℃
    material_properties JSONB, -- 其他材料特性
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入金属材料基础数据
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

-- 5. 模具信息主表
CREATE TABLE IF NOT EXISTS molds (
    mold_id SERIAL PRIMARY KEY,
    mold_code VARCHAR(100) UNIQUE NOT NULL, -- 模具编号
    mold_name VARCHAR(255) NOT NULL, -- 模具名称
    mold_drawing_number VARCHAR(100), -- 模具图号
    
    -- 模具分类和规格
    mold_functional_type_id INTEGER REFERENCES mold_functional_types(type_id),
    specification JSONB, -- 模具规格 (长x宽x高等)
    weight_kg DECIMAL(10,3), -- 模具重量(kg)
    
    -- 适用材料和产品
    applicable_materials INTEGER[] DEFAULT '{}', -- 适用材料ID数组
    target_product_specs TEXT, -- 目标产品规格
    
    -- 制造信息
    manufacturer VARCHAR(255), -- 制作人/制造商
    manufacturing_date DATE, -- 制造日期
    acceptance_date DATE, -- 验收日期
    purchase_cost DECIMAL(12,2), -- 采购成本
    
    -- 寿命管理
    theoretical_lifespan_strokes INTEGER, -- 理论寿命冲次
    accumulated_strokes INTEGER DEFAULT 0, -- 当前已累计冲次
    remaining_strokes INTEGER, -- 剩余冲次(计算字段)
    maintenance_cycle_strokes INTEGER, -- 保养周期冲次
    last_maintenance_strokes INTEGER DEFAULT 0, -- 上次保养时的冲次
    
    -- 当前状态
    current_status_id INTEGER NOT NULL REFERENCES mold_statuses(status_id),
    current_location_id INTEGER REFERENCES storage_locations(location_id),
    responsible_person_id INTEGER, -- 责任人ID (暂时用整数，后续关联用户表)
    
    -- 技术文档
    design_drawing_link TEXT, -- 设计图纸链接
    technical_docs JSONB, -- 技术文档 JSON
    image_paths TEXT[], -- 模具图片路径数组
    qr_code VARCHAR(255), -- 二维码内容
    
    -- 特殊标记
    has_coating BOOLEAN DEFAULT FALSE, -- 是否有涂层
    is_precision_mold BOOLEAN DEFAULT FALSE, -- 是否精密模具
    priority_level INTEGER DEFAULT 3, -- 优先级(1-5, 5最高)
    
    -- 备注信息
    remarks TEXT,
    project_number VARCHAR(100), -- 项目编号
    associated_equipment_number VARCHAR(100), -- 配套设备编号
    
    -- 时间戳
    entry_date DATE DEFAULT CURRENT_DATE, -- 入账日期
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 添加计算字段的触发器
CREATE OR REPLACE FUNCTION update_remaining_strokes()
RETURNS TRIGGER AS $$
BEGIN
    -- 计算剩余冲次
    IF NEW.theoretical_lifespan_strokes IS NOT NULL THEN
        NEW.remaining_strokes = NEW.theoretical_lifespan_strokes - NEW.accumulated_strokes;
    END IF;
    
    -- 更新时间戳
    NEW.updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mold_fields
    BEFORE INSERT OR UPDATE ON molds
    FOR EACH ROW
    EXECUTE FUNCTION update_remaining_strokes();

-- 6. 模具使用记录表 (简化版)
CREATE TABLE IF NOT EXISTS mold_usage_records (
    usage_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id) ON DELETE CASCADE,
    operator_name VARCHAR(100), -- 操作工姓名 (暂时用字符串)
    equipment_id VARCHAR(100), -- 使用设备编号
    production_order_number VARCHAR(100), -- 生产订单号
    
    -- 使用时间
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ,
    duration_minutes INTEGER, -- 使用时长(分钟)
    
    -- 生产数据
    strokes_this_session INTEGER NOT NULL DEFAULT 0, -- 本次使用冲次
    produced_quantity INTEGER, -- 生产数量
    qualified_quantity INTEGER, -- 合格品数量
    defect_quantity INTEGER, -- 不良品数量
    
    -- 备注
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 使用记录更新模具累计冲次的触发器
CREATE OR REPLACE FUNCTION update_mold_strokes()
RETURNS TRIGGER AS $$
BEGIN
    -- 当插入或更新使用记录时，更新模具的累计冲次
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.strokes_this_session != NEW.strokes_this_session) THEN
        UPDATE molds 
        SET accumulated_strokes = accumulated_strokes + NEW.strokes_this_session - COALESCE(OLD.strokes_this_session, 0)
        WHERE mold_id = NEW.mold_id;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mold_strokes
    AFTER INSERT OR UPDATE ON mold_usage_records
    FOR EACH ROW
    EXECUTE FUNCTION update_mold_strokes();

-- 7. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_molds_code ON molds(mold_code);
CREATE INDEX IF NOT EXISTS idx_molds_name ON molds(mold_name);
CREATE INDEX IF NOT EXISTS idx_molds_status ON molds(current_status_id);
CREATE INDEX IF NOT EXISTS idx_molds_location ON molds(current_location_id);
CREATE INDEX IF NOT EXISTS idx_molds_type ON molds(mold_functional_type_id);
CREATE INDEX IF NOT EXISTS idx_molds_accumulated_strokes ON molds(accumulated_strokes);
CREATE INDEX IF NOT EXISTS idx_usage_records_mold_id ON mold_usage_records(mold_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_timestamp ON mold_usage_records(start_timestamp);

-- 8. 创建视图以便查询
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
    m.remaining_strokes,
    CASE 
        WHEN m.theoretical_lifespan_strokes > 0 THEN 
            ROUND((m.accumulated_strokes::DECIMAL / m.theoretical_lifespan_strokes * 100), 2)
        ELSE 0 
    END as usage_percentage,
    m.has_coating,
    m.is_precision_mold,
    m.priority_level,
    m.entry_date,
    m.created_at,
    m.updated_at
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
WHERE mft.is_active = TRUE;

-- 插入测试数据
INSERT INTO molds (
    mold_code, mold_name, mold_functional_type_id, current_status_id, current_location_id,
    theoretical_lifespan_strokes, maintenance_cycle_strokes, manufacturer, 
    specification, has_coating, priority_level, remarks
) VALUES
(
    'MD001', 'Φ50钛平底杯落料模', 1, 1, 1,
    100000, 5000, '模具工张师傅',
    '{"diameter": 50, "depth": 30, "material": "钛", "tolerance": "±0.1"}',
    TRUE, 4, '高精度落料模，适用于钛材加工'
),
(
    'MD002', 'Φ50钛平底杯一引模', 2, 1, 2,
    80000, 4000, '模具工张师傅',
    '{"diameter": 50, "depth": 15, "material": "钛", "tolerance": "±0.05"}',
    TRUE, 4, '第一次拉伸成型模具'
),
(
    'MD003', 'Φ30钼圆片落料模', 1, 2, 8,
    120000, 6000, '模具工李师傅',
    '{"diameter": 30, "thickness": 2, "material": "钼", "tolerance": "±0.02"}',
    FALSE, 3, '钼材圆片落料专用模具'
);

-- 创建一些使用记录
INSERT INTO mold_usage_records (
    mold_id, operator_name, equipment_id, production_order_number,
    start_timestamp, end_timestamp, strokes_this_session, produced_quantity, qualified_quantity
) VALUES
(1, '操作工王师傅', 'PRESS001', 'PO2025001', 
 NOW() - INTERVAL '2 hours', NOW() - INTERVAL '30 minutes', 150, 150, 148),
(1, '操作工李师傅', 'PRESS001', 'PO2025002', 
 NOW() - INTERVAL '1 day', NOW() - INTERVAL '23 hours', 200, 200, 195),
(2, '操作工张师傅', 'PRESS002', 'PO2025003', 
 NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', 80, 80, 80);

-- 显示创建结果
SELECT 'Database schema created successfully!' as result;