-- 模具管理系统 - 核心表结构

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

-- 2. 模具状态字典表
CREATE TABLE IF NOT EXISTS mold_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    status_code VARCHAR(20) UNIQUE NOT NULL,
    status_color VARCHAR(10) DEFAULT '#666666',
    description TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 存放位置字典表
CREATE TABLE IF NOT EXISTS storage_locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    location_code VARCHAR(20) UNIQUE NOT NULL,
    area VARCHAR(50),
    rack_number VARCHAR(20),
    level_number VARCHAR(10),
    capacity INTEGER DEFAULT 0,
    current_count INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 金属材料表
CREATE TABLE IF NOT EXISTS materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(100) UNIQUE NOT NULL,
    material_code VARCHAR(20) UNIQUE NOT NULL,
    density DECIMAL(8,4),
    hardness VARCHAR(50),
    melting_point INTEGER,
    material_properties JSONB,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 模具信息主表
CREATE TABLE IF NOT EXISTS molds (
    mold_id SERIAL PRIMARY KEY,
    mold_code VARCHAR(100) UNIQUE NOT NULL,
    mold_name VARCHAR(255) NOT NULL,
    mold_drawing_number VARCHAR(100),
    mold_functional_type_id INTEGER REFERENCES mold_functional_types(type_id),
    specification JSONB,
    weight_kg DECIMAL(10,3),
    applicable_materials INTEGER[] DEFAULT '{}',
    target_product_specs TEXT,
    manufacturer VARCHAR(255),
    manufacturing_date DATE,
    acceptance_date DATE,
    purchase_cost DECIMAL(12,2),
    theoretical_lifespan_strokes INTEGER,
    accumulated_strokes INTEGER DEFAULT 0,
    remaining_strokes INTEGER,
    maintenance_cycle_strokes INTEGER,
    last_maintenance_strokes INTEGER DEFAULT 0,
    current_status_id INTEGER NOT NULL REFERENCES mold_statuses(status_id),
    current_location_id INTEGER REFERENCES storage_locations(location_id),
    responsible_person_id INTEGER,
    design_drawing_link TEXT,
    technical_docs JSONB,
    image_paths TEXT[],
    qr_code VARCHAR(255),
    has_coating BOOLEAN DEFAULT FALSE,
    is_precision_mold BOOLEAN DEFAULT FALSE,
    priority_level INTEGER DEFAULT 3,
    remarks TEXT,
    project_number VARCHAR(100),
    associated_equipment_number VARCHAR(100),
    entry_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. 模具使用记录表
CREATE TABLE IF NOT EXISTS mold_usage_records (
    usage_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL REFERENCES molds(mold_id) ON DELETE CASCADE,
    operator_name VARCHAR(100),
    equipment_id VARCHAR(100),
    production_order_number VARCHAR(100),
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ,
    duration_minutes INTEGER,
    strokes_this_session INTEGER NOT NULL DEFAULT 0,
    produced_quantity INTEGER,
    qualified_quantity INTEGER,
    defect_quantity INTEGER,
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_molds_code ON molds(mold_code);
CREATE INDEX IF NOT EXISTS idx_molds_name ON molds(mold_name);
CREATE INDEX IF NOT EXISTS idx_molds_status ON molds(current_status_id);
CREATE INDEX IF NOT EXISTS idx_molds_location ON molds(current_location_id);
CREATE INDEX IF NOT EXISTS idx_molds_type ON molds(mold_functional_type_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_mold_id ON mold_usage_records(mold_id);
