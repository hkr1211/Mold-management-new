-- 模具管理系统数据库初始化脚本
-- 创建数据库（如果不存在）
-- CREATE DATABASE IF NOT EXISTS mold_management;

-- 使用数据库
-- \c mold_management;

-- 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 创建用户表
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

-- 创建模具功能类型表
CREATE TABLE IF NOT EXISTS mold_functional_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 创建模具状态字典表
CREATE TABLE IF NOT EXISTS mold_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 创建存放位置字典表
CREATE TABLE IF NOT EXISTS storage_locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 创建模具信息主表
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

-- 创建模具部件分类字典表
CREATE TABLE IF NOT EXISTS mold_part_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 创建模具部件表
CREATE TABLE IF NOT EXISTS mold_parts (
    part_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id) ON DELETE CASCADE,
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

-- 创建产品类型字典表
CREATE TABLE IF NOT EXISTS product_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- 创建金属材料表
CREATE TABLE IF NOT EXISTS materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(100) UNIQUE NOT NULL,
    material_properties JSONB,
    description TEXT
);

-- 创建产品信息表
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

-- 创建产品工艺流程表
CREATE TABLE IF NOT EXISTS product_process_flow (
    flow_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id),
    sequence_order INTEGER NOT NULL,
    process_step_name VARCHAR(255),
    remarks TEXT,
    UNIQUE (product_id, sequence_order)
);

-- 创建借用状态字典表
CREATE TABLE IF NOT EXISTS loan_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 创建模具借用记录表
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

-- 创建模具使用记录表
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

-- 创建维修保养类型字典表
CREATE TABLE IF NOT EXISTS maintenance_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    is_repair BOOLEAN NOT NULL,
    description TEXT
);

-- 创建维修保养结果状态字典表
CREATE TABLE IF NOT EXISTS maintenance_result_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 创建模具维修保养记录表
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

-- 创建系统操作日志表
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

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_molds_code ON molds(mold_code);
CREATE INDEX IF NOT EXISTS idx_molds_status ON molds(current_status_id);
CREATE INDEX IF NOT EXISTS idx_molds_location ON molds(current_location_id);
CREATE INDEX IF NOT EXISTS idx_mold_parts_mold_id ON mold_parts(mold_id);
CREATE INDEX IF NOT EXISTS idx_loan_records_mold_id ON mold_loan_records(mold_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_mold_id ON mold_usage_records(mold_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_mold_id ON mold_maintenance_logs(mold_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);

-- 创建触发器函数用于自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_molds_updated_at BEFORE UPDATE ON molds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mold_parts_updated_at BEFORE UPDATE ON mold_parts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();