-- 数据库表结构修复脚本
-- 解决 supplier 字段缺失等问题

-- 添加 molds 表缺失的字段
ALTER TABLE molds ADD COLUMN IF NOT EXISTS supplier VARCHAR(255);
ALTER TABLE molds ADD COLUMN IF NOT EXISTS manufacturing_date DATE;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS acceptance_date DATE;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS theoretical_lifespan_strokes INTEGER;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS accumulated_strokes INTEGER DEFAULT 0;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS maintenance_cycle_strokes INTEGER;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS design_drawing_link TEXT;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS image_path TEXT;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS remarks TEXT;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS project_number VARCHAR(100);
ALTER TABLE molds ADD COLUMN IF NOT EXISTS associated_equipment_number VARCHAR(100);
ALTER TABLE molds ADD COLUMN IF NOT EXISTS entry_date DATE DEFAULT CURRENT_DATE;
ALTER TABLE molds ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE molds ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 为现有记录设置默认值
UPDATE molds SET accumulated_strokes = 0 WHERE accumulated_strokes IS NULL;
UPDATE molds SET entry_date = CURRENT_DATE WHERE entry_date IS NULL;
UPDATE molds SET created_at = NOW() WHERE created_at IS NULL;
UPDATE molds SET updated_at = NOW() WHERE updated_at IS NULL;

-- 修复 mold_usage_records 表
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS operator_id INTEGER REFERENCES users(user_id);
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS equipment_id VARCHAR(100);
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS production_order_number VARCHAR(100);
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS product_id_produced INTEGER REFERENCES products(product_id);
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS start_timestamp TIMESTAMPTZ;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS end_timestamp TIMESTAMPTZ;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS strokes_this_session INTEGER DEFAULT 0;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS produced_quantity INTEGER;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS qualified_quantity INTEGER;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE mold_usage_records ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ DEFAULT NOW();

-- 为现有记录设置默认值
UPDATE mold_usage_records SET strokes_this_session = 0 WHERE strokes_this_session IS NULL;
UPDATE mold_usage_records SET recorded_at = NOW() WHERE recorded_at IS NULL;

-- 验证修复结果
SELECT 'molds表字段检查' as table_name, column_name 
FROM information_schema.columns 
WHERE table_name = 'molds' 
ORDER BY ordinal_position;

SELECT 'mold_usage_records表字段检查' as table_name, column_name 
FROM information_schema.columns 
WHERE table_name = 'mold_usage_records' 
ORDER BY ordinal_position;