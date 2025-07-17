-- 数据库初始化脚本
-- 创建所有必要的表和基础数据

-- 1. 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 2. 创建用户表
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    email VARCHAR(100) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. 创建模具功能类型表
CREATE TABLE IF NOT EXISTS mold_functional_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 4. 创建模具状态字典表
CREATE TABLE IF NOT EXISTS mold_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 5. 创建存放位置字典表
CREATE TABLE IF NOT EXISTS storage_locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 6. 创建模具信息主表
CREATE TABLE IF NOT EXISTS molds (
    mold_id SERIAL PRIMARY KEY,
    mold_code VARCHAR(100) UNIQUE NOT NULL,
    mold_name VARCHAR(255) NOT NULL,
    mold_drawing_number VARCHAR(100),
    mold_functional_type_id INTEGER REFERENCES mold_functional_types(type_id),
    supplier VARCHAR(255),
    manufacturing_date DATE,
    acceptance_date DATE,
    theoretical_lifespan_strokes INTEGER,
    accumulated_strokes INTEGER DEFAULT 0,
    maintenance_cycle_strokes INTEGER,
    current_status_id INTEGER NOT NULL REFERENCES mold_statuses(status_id),
    current_location_id INTEGER REFERENCES storage_locations(location_id),
    responsible_person_id INTEGER REFERENCES users(user_id),
    design_drawing_link TEXT,
    image_path TEXT,
    remarks TEXT,
    project_number VARCHAR(100),
    associated_equipment_number VARCHAR(100),
    entry_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. 创建模具部件分类字典表
CREATE TABLE IF NOT EXISTS mold_part_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 8. 创建模具部件表
CREATE TABLE IF NOT EXISTS mold_parts (
    part_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id),
    part_code VARCHAR(100) UNIQUE,
    part_name VARCHAR(255) NOT NULL,
    part_category_id INTEGER NOT NULL REFERENCES mold_part_categories(category_id),
    material VARCHAR(100),
    supplier VARCHAR(255),
    installation_date DATE,
    lifespan_strokes INTEGER,
    current_status_id INTEGER REFERENCES mold_statuses(status_id),
    remarks TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. 创建产品类型字典表
CREATE TABLE IF NOT EXISTS product_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 10. 创建金属材料表
CREATE TABLE IF NOT EXISTS materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(100) UNIQUE NOT NULL,
    material_properties JSONB,
    description TEXT
);

-- 11. 创建产品信息表
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_drawing_number VARCHAR(100),
    product_type_id INTEGER NOT NULL REFERENCES product_types(type_id),
    material_id INTEGER NOT NULL REFERENCES materials(material_id),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. 创建产品工艺流程表
CREATE TABLE IF NOT EXISTS product_process_flow (
    flow_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id),
    sequence_order INTEGER NOT NULL,
    process_step_name VARCHAR(255),
    remarks TEXT,
    UNIQUE (product_id, sequence_order)
);

-- 13. 创建借用状态字典表
CREATE TABLE IF NOT EXISTS loan_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 14. 创建模具借用记录表
CREATE TABLE IF NOT EXISTS mold_loan_records (
    loan_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id),
    applicant_id INTEGER NOT NULL REFERENCES users(user_id),
    application_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approver_id INTEGER REFERENCES users(user_id),
    approval_timestamp TIMESTAMPTZ,
    loan_out_timestamp TIMESTAMPTZ,
    expected_return_timestamp TIMESTAMPTZ,
    actual_return_timestamp TIMESTAMPTZ,
    loan_status_id INTEGER NOT NULL REFERENCES loan_statuses(status_id),
    destination_equipment VARCHAR(100),
    remarks TEXT
);

-- 15. 创建模具使用记录表
CREATE TABLE IF NOT EXISTS mold_usage_records (
    usage_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id),
    operator_id INTEGER NOT NULL REFERENCES users(user_id),
    equipment_id VARCHAR(100),
    production_order_number VARCHAR(100),
    product_id_produced INTEGER REFERENCES products(product_id),
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ,
    strokes_this_session INTEGER NOT NULL,
    produced_quantity INTEGER,
    qualified_quantity INTEGER,
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. 创建维修保养类型字典表
CREATE TABLE IF NOT EXISTS maintenance_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    is_repair BOOLEAN NOT NULL,
    description TEXT
);

-- 17. 创建维修保养结果状态字典表
CREATE TABLE IF NOT EXISTS maintenance_result_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 18. 创建模具维修保养记录表
CREATE TABLE IF NOT EXISTS mold_maintenance_logs (
    log_id SERIAL PRIMARY KEY,
    mold_id INTEGER REFERENCES molds(mold_id),
    part_id INTEGER REFERENCES mold_parts(part_id),
    maintenance_type_id INTEGER NOT NULL REFERENCES maintenance_types(type_id),
    problem_description TEXT,
    actions_taken TEXT,
    maintenance_start_timestamp TIMESTAMPTZ NOT NULL,
    maintenance_end_timestamp TIMESTAMPTZ,
    maintained_by_id INTEGER NOT NULL REFERENCES users(user_id),
    replaced_parts_info JSONB,
    maintenance_cost DECIMAL(10,2),
    result_status_id INTEGER NOT NULL REFERENCES maintenance_result_statuses(status_id),
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 19. 创建系统操作日志表
CREATE TABLE IF NOT EXISTS system_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    action_type VARCHAR(100) NOT NULL,
    target_resource VARCHAR(100),
    target_id VARCHAR(100),
    details JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 插入基础数据

-- 角色数据
INSERT INTO roles (role_name, description) VALUES 
('超级管理员', '系统管理员，拥有所有权限'),
('模具库管理员', '负责模具台账管理、借用管理等'),
('模具工', '负责模具维修保养工作'),
('冲压操作工', '负责模具使用和借用申请')
ON CONFLICT (role_name) DO NOTHING;

-- 默认用户数据
INSERT INTO users (username, password_hash, full_name, role_id, email) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8ixM8/XMhe', '系统管理员', 1, 'admin@company.com'),
('mold_admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8ixM8/XMhe', '模具库管理员', 2, 'mold@company.com'),
('technician', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8ixM8/XMhe', '模具工师傅', 3, 'tech@company.com'),
('operator', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8ixM8/XMhe', '冲压操作工', 4, 'op@company.com')
ON CONFLICT (username) DO NOTHING;

-- 模具功能类型数据
INSERT INTO mold_functional_types (type_name, description) VALUES 
('落料模', '用于材料下料的模具'),
('一引模', '第一道拉伸成型模具'),
('二引模', '第二道拉伸成型模具'),
('三引模', '第三道拉伸成型模具'),
('四引模', '第四道拉伸成型模具'),
('切边模', '用于产品切边的模具')
ON CONFLICT (type_name) DO NOTHING;

-- 模具状态数据
INSERT INTO mold_statuses (status_name, description) VALUES 
('闲置', '模具可用状态'),
('使用中', '模具正在使用'),
('已借出', '模具已被借出'),
('维修中', '模具正在维修'),
('保养中', '模具正在保养'),
('待维修', '模具需要维修'),
('待保养', '模具需要保养'),
('报废', '模具已报废')
ON CONFLICT (status_name) DO NOTHING;

-- 存放位置数据
INSERT INTO storage_locations (location_name, description) VALUES 
('模具库A1', 'A区第1排货架'),
('模具库A2', 'A区第2排货架'),
('模具库A3', 'A区第3排货架'),
('模具库B1', 'B区第1排货架'),
('模具库B2', 'B区第2排货架'),
('模具库B3', 'B区第3排货架'),
('维修车间', '维修保养区域'),
('生产车间1', '1号生产车间'),
('生产车间2', '2号生产车间')
ON CONFLICT (location_name) DO NOTHING;

-- 部件分类数据
INSERT INTO mold_part_categories (category_name, description) VALUES 
('模架', '模具框架部分'),
('上模', '模具上半部分'),
('下模', '模具下半部分'),
('芯子', '模具芯子部件'),
('压边圈', '控制材料流动的压边圈')
ON CONFLICT (category_name) DO NOTHING;

-- 产品类型数据
INSERT INTO product_types (type_name, description) VALUES 
('平底圆杯', '平底圆形杯状产品'),
('异形杯', '非标准形状杯状产品'),
('金属圆片', '圆形片状产品')
ON CONFLICT (type_name) DO NOTHING;

-- 金属材料数据
INSERT INTO materials (material_name, description) VALUES 
('钛', '钛合金材料'),
('钼', '钼合金材料'),
('锆', '锆合金材料'),
('铌', '铌合金材料'),
('钽', '钽合金材料'),
('钴', '钴合金材料'),
('铜', '铜合金材料'),
('铁', '铁合金材料')
ON CONFLICT (material_name) DO NOTHING;

-- 借用状态数据
INSERT INTO loan_statuses (status_name, description) VALUES 
('待审批', '申请已提交，等待审批'),
('已批准', '申请已批准，等待领用'),
('已领用', '模具已领用'),
('已归还', '模具已归还'),
('已驳回', '申请被驳回'),
('逾期', '超过预期归还时间')
ON CONFLICT (status_name) DO NOTHING;

-- 维修保养类型数据
INSERT INTO maintenance_types (type_name, is_repair, description) VALUES 
('日常保养', FALSE, '日常清洁保养'),
('定期保养', FALSE, '定期维护保养'),
('故障维修', TRUE, '故障修复'),
('预防性维修', TRUE, '预防性维修'),
('改进升级', TRUE, '模具改进升级')
ON CONFLICT (type_name) DO NOTHING;

-- 维修结果状态数据
INSERT INTO maintenance_result_statuses (status_name, description) VALUES 
('完成待检', '维修完成，等待检验'),
('合格可用', '检验合格，可以使用'),
('失败待查', '维修失败，需要进一步检查'),
('等待备件', '等待备件到货'),
('需要外协', '需要外部协助')
ON CONFLICT (status_name) DO NOTHING;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_molds_code ON molds(mold_code);
CREATE INDEX IF NOT EXISTS idx_molds_status ON molds(current_status_id);
CREATE INDEX IF NOT EXISTS idx_molds_location ON molds(current_location_id);
CREATE INDEX IF NOT EXISTS idx_mold_parts_mold_id ON mold_parts(mold_id);
CREATE INDEX IF NOT EXISTS idx_loan_records_mold_id ON mold_loan_records(mold_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_mold_id ON mold_usage_records(mold_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_mold_id ON mold_maintenance_logs(mold_id);