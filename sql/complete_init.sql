-- sql/complete_init.sql
-- 完整的数据库初始化脚本

-- 1. 确保基础状态数据完整
INSERT INTO mold_statuses (status_name, description) VALUES 
('闲置', '模具可用状态'),
('使用中', '模具正在使用'),
('已借出', '模具已被借出'),
('已预定', '模具已预定待借出'),
('外借申请中', '模具正在处理借用申请'),
('维修中', '模具正在维修'),
('保养中', '模具正在保养'),
('待维修', '模具需要维修'),
('待保养', '模具需要保养'),
('报废', '模具已报废')
ON CONFLICT (status_name) DO UPDATE SET description = EXCLUDED.description;

-- 2. 确保借用状态数据完整
INSERT INTO loan_statuses (status_name, description) VALUES 
('待审批', '申请已提交，等待审批'),
('已批准', '申请已批准，等待处理'),
('已批准待借出', '申请已批准，等待借出'),
('已借出', '模具已借出使用'),
('已归还', '模具已归还'),
('已驳回', '申请被驳回'),
('逾期', '超过预期归还时间'),
('外借申请中', '申请处理中，模具预留状态')
ON CONFLICT (status_name) DO UPDATE SET description = EXCLUDED.description;

-- 3. 确保维修结果状态完整
INSERT INTO maintenance_result_statuses (status_name, description) VALUES 
('待开始', '任务已创建，等待开始执行'),
('进行中', '维修保养工作正在进行'),
('完成待检', '维修保养完成，等待质量检验'),
('合格可用', '检验合格，可以正常使用'),
('失败待查', '维修失败，需要进一步分析'),
('等待备件', '等待备件到货后继续'),
('需要外协', '需要外部专业机构协助')
ON CONFLICT (status_name) DO UPDATE SET description = EXCLUDED.description;

-- 4. 添加生产相关的基础数据
-- 设备信息表（用于排程）
CREATE TABLE IF NOT EXISTS production_equipment (
    equipment_id SERIAL PRIMARY KEY,
    equipment_code VARCHAR(50) UNIQUE NOT NULL,
    equipment_name VARCHAR(100) NOT NULL,
    equipment_type VARCHAR(50), -- 冲压机类型
    tonnage INTEGER, -- 吨位
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 生产订单表（简化版，用于关联）
CREATE TABLE IF NOT EXISTS production_orders (
    order_id SERIAL PRIMARY KEY,
    order_code VARCHAR(100) UNIQUE NOT NULL,
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    due_date DATE,
    priority INTEGER DEFAULT 5, -- 1-10, 1最高
    status VARCHAR(50) DEFAULT '待排程',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 模具推荐记录表
CREATE TABLE IF NOT EXISTS mold_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES production_orders(order_id),
    mold_id INTEGER REFERENCES molds(mold_id),
    recommendation_score DECIMAL(5,2), -- 推荐分数
    recommendation_reason TEXT,
    is_selected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 生产排程表
CREATE TABLE IF NOT EXISTS production_schedules (
    schedule_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES production_orders(order_id),
    mold_id INTEGER REFERENCES molds(mold_id),
    equipment_id INTEGER REFERENCES production_equipment(equipment_id),
    operator_id INTEGER REFERENCES users(user_id),
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT '待执行',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 成本记录表
CREATE TABLE IF NOT EXISTS cost_records (
    cost_id SERIAL PRIMARY KEY,
    cost_type VARCHAR(50) NOT NULL, -- 维修成本、停机损失、材料成本等
    related_type VARCHAR(50), -- mold, maintenance, production等
    related_id INTEGER,
    amount DECIMAL(10,2) NOT NULL,
    cost_date DATE DEFAULT CURRENT_DATE,
    description TEXT,
    created_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 插入示例设备数据
INSERT INTO production_equipment (equipment_code, equipment_name, equipment_type, tonnage) VALUES 
('PRESS-01', '1号冲压机', '液压式', 100),
('PRESS-02', '2号冲压机', '液压式', 150),
('PRESS-03', '3号冲压机', '机械式', 80),
('PRESS-04', '4号冲压机', '伺服式', 200)
ON CONFLICT (equipment_code) DO NOTHING;

-- 6. 创建有用的视图
-- 模具使用状态视图
CREATE OR REPLACE VIEW v_mold_status_overview AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    mft.type_name as mold_type,
    ms.status_name as current_status,
    sl.location_name as current_location,
    m.theoretical_lifespan_strokes,
    m.accumulated_strokes,
    CASE 
        WHEN m.theoretical_lifespan_strokes > 0 
        THEN ROUND((m.accumulated_strokes::DECIMAL / m.theoretical_lifespan_strokes) * 100, 2)
        ELSE 0
    END as usage_percentage,
    m.theoretical_lifespan_strokes - m.accumulated_strokes as remaining_strokes,
    m.maintenance_cycle_strokes,
    CASE 
        WHEN m.maintenance_cycle_strokes > 0 
        THEN m.accumulated_strokes - (m.accumulated_strokes / m.maintenance_cycle_strokes) * m.maintenance_cycle_strokes
        ELSE 0
    END as strokes_since_maintenance
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id;

-- 模具成本汇总视图
CREATE OR REPLACE VIEW v_mold_cost_summary AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    COALESCE(SUM(CASE WHEN cr.cost_type = '维修成本' THEN cr.amount ELSE 0 END), 0) as total_maintenance_cost,
    COALESCE(SUM(CASE WHEN cr.cost_type = '停机损失' THEN cr.amount ELSE 0 END), 0) as total_downtime_cost,
    COALESCE(SUM(cr.amount), 0) as total_cost,
    COUNT(DISTINCT mml.log_id) as maintenance_count,
    MAX(mml.maintenance_end_timestamp) as last_maintenance_date
FROM molds m
LEFT JOIN cost_records cr ON cr.related_type = 'mold' AND cr.related_id = m.mold_id
LEFT JOIN mold_maintenance_logs mml ON mml.mold_id = m.mold_id
GROUP BY m.mold_id, m.mold_code, m.mold_name;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_cost_records_related ON cost_records(related_type, related_id);
CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_schedules_dates ON production_schedules(scheduled_start, scheduled_end);
CREATE INDEX IF NOT EXISTS idx_mold_recommendations_order ON mold_recommendations(order_id, recommendation_score DESC);