-- 保养周期管理数据库更新脚本 - 完整修正版
-- 执行前请备份数据库！

-- 开始事务
BEGIN;

-- 记录脚本开始执行
DO $$
BEGIN
    RAISE NOTICE '=================================================';
    RAISE NOTICE '开始执行保养周期管理数据库更新脚本';
    RAISE NOTICE '执行时间: %', NOW();
    RAISE NOTICE '=================================================';
END $$;

-- 1. 检查并更新molds表结构
DO $$
BEGIN
    RAISE NOTICE '1. 更新molds表结构...';
    
    -- 检查现有字段名称（可能是maintenance_cycle_strokes而不是current_maintenance_cycle_strokes）
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'maintenance_cycle_strokes') THEN
        -- 如果是旧字段名，重命名为新字段名
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'current_maintenance_cycle_strokes') THEN
            ALTER TABLE molds RENAME COLUMN maintenance_cycle_strokes TO current_maintenance_cycle_strokes;
            RAISE NOTICE '  - 重命名字段: maintenance_cycle_strokes -> current_maintenance_cycle_strokes';
        END IF;
    END IF;

    -- 添加初始保养周期字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'initial_maintenance_cycle_strokes') THEN
        ALTER TABLE molds ADD COLUMN initial_maintenance_cycle_strokes INTEGER;
        RAISE NOTICE '  - 添加字段: initial_maintenance_cycle_strokes';
    END IF;

    -- 确保当前保养周期字段存在
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'current_maintenance_cycle_strokes') THEN
        ALTER TABLE molds ADD COLUMN current_maintenance_cycle_strokes INTEGER DEFAULT 10000;
        RAISE NOTICE '  - 添加字段: current_maintenance_cycle_strokes';
    END IF;
    
    -- 设置字段属性和约束
    ALTER TABLE molds ALTER COLUMN current_maintenance_cycle_strokes SET NOT NULL;
    ALTER TABLE molds ALTER COLUMN current_maintenance_cycle_strokes SET DEFAULT 10000;

    -- 添加上次保养冲次记录
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'last_maintenance_strokes') THEN
        ALTER TABLE molds ADD COLUMN last_maintenance_strokes INTEGER DEFAULT 0;
        RAISE NOTICE '  - 添加字段: last_maintenance_strokes';
    END IF;

    -- 添加保养周期调整次数
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'maintenance_cycle_adjustment_count') THEN
        ALTER TABLE molds ADD COLUMN maintenance_cycle_adjustment_count INTEGER DEFAULT 0;
        RAISE NOTICE '  - 添加字段: maintenance_cycle_adjustment_count';
    END IF;

    -- 添加保养提醒设置
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'enable_auto_reminder') THEN
        ALTER TABLE molds ADD COLUMN enable_auto_reminder BOOLEAN DEFAULT TRUE;
        RAISE NOTICE '  - 添加字段: enable_auto_reminder';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'reminder_advance_strokes') THEN
        ALTER TABLE molds ADD COLUMN reminder_advance_strokes INTEGER DEFAULT 1000;
        RAISE NOTICE '  - 添加字段: reminder_advance_strokes';
    END IF;

    -- 添加保养优先级
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'maintenance_priority') THEN
        ALTER TABLE molds ADD COLUMN maintenance_priority VARCHAR(20) DEFAULT '普通';
        RAISE NOTICE '  - 添加字段: maintenance_priority';
    END IF;

    -- 添加预计保养耗时
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'estimated_maintenance_hours') THEN
        ALTER TABLE molds ADD COLUMN estimated_maintenance_hours DECIMAL(4,2) DEFAULT 2.0;
        RAISE NOTICE '  - 添加字段: estimated_maintenance_hours';
    END IF;

    -- 添加涂层标记
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'molds' AND column_name = 'has_coating') THEN
        ALTER TABLE molds ADD COLUMN has_coating BOOLEAN DEFAULT FALSE;
        RAISE NOTICE '  - 添加字段: has_coating';
    END IF;

    -- 添加字段注释
    COMMENT ON COLUMN molds.initial_maintenance_cycle_strokes IS '初始设定的保养周期冲次';
    COMMENT ON COLUMN molds.current_maintenance_cycle_strokes IS '当前有效的保养周期冲次';
    COMMENT ON COLUMN molds.last_maintenance_strokes IS '上次保养时的累计冲次';
    COMMENT ON COLUMN molds.maintenance_cycle_adjustment_count IS '保养周期调整次数';
    COMMENT ON COLUMN molds.enable_auto_reminder IS '是否启用自动保养提醒';
    COMMENT ON COLUMN molds.reminder_advance_strokes IS '提前提醒的冲次数';
    COMMENT ON COLUMN molds.maintenance_priority IS '保养优先级：普通、重要、关键';
    COMMENT ON COLUMN molds.estimated_maintenance_hours IS '预计保养耗时（小时）';
    COMMENT ON COLUMN molds.has_coating IS '是否有表面涂层';

    -- 添加约束
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'molds_positive_cycle_strokes') THEN
        ALTER TABLE molds ADD CONSTRAINT molds_positive_cycle_strokes 
        CHECK (current_maintenance_cycle_strokes > 0);
        RAISE NOTICE '  - 添加约束: molds_positive_cycle_strokes';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'molds_valid_priority') THEN
        ALTER TABLE molds ADD CONSTRAINT molds_valid_priority 
        CHECK (maintenance_priority IN ('普通', '重要', '关键'));
        RAISE NOTICE '  - 添加约束: molds_valid_priority';
    END IF;

    RAISE NOTICE '  molds表结构更新完成';
END $$;

-- 2. 创建保养周期调整历史表
DO $$
BEGIN
    RAISE NOTICE '2. 创建保养周期调整历史表...';
END $$;

CREATE TABLE IF NOT EXISTS mold_maintenance_cycle_history (
    history_id SERIAL PRIMARY KEY,
    mold_id INTEGER NOT NULL,
    old_cycle_strokes INTEGER,
    new_cycle_strokes INTEGER NOT NULL,
    adjustment_reason TEXT NOT NULL,
    adjusted_by_user_id INTEGER NOT NULL,
    adjustment_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accumulated_strokes_at_adjustment INTEGER DEFAULT 0,
    remarks TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_cycle_history_mold FOREIGN KEY (mold_id) REFERENCES molds(mold_id) ON DELETE CASCADE,
    CONSTRAINT fk_cycle_history_user FOREIGN KEY (adjusted_by_user_id) REFERENCES users(user_id),
    CONSTRAINT valid_new_cycle_strokes CHECK (new_cycle_strokes > 0),
    CONSTRAINT valid_old_cycle_strokes CHECK (old_cycle_strokes IS NULL OR old_cycle_strokes > 0),
    CONSTRAINT valid_accumulated_strokes_history CHECK (accumulated_strokes_at_adjustment >= 0)
);

COMMENT ON TABLE mold_maintenance_cycle_history IS '模具保养周期调整历史记录表';
COMMENT ON COLUMN mold_maintenance_cycle_history.old_cycle_strokes IS '调整前的保养周期冲次';
COMMENT ON COLUMN mold_maintenance_cycle_history.new_cycle_strokes IS '调整后的保养周期冲次';
COMMENT ON COLUMN mold_maintenance_cycle_history.adjustment_reason IS '调整原因';
COMMENT ON COLUMN mold_maintenance_cycle_history.accumulated_strokes_at_adjustment IS '调整时模具的累计冲次';

-- 3. 创建模具类型默认保养周期表
DO $$
BEGIN
    RAISE NOTICE '3. 创建模具类型默认保养周期表...';
END $$;

CREATE TABLE IF NOT EXISTS mold_type_default_maintenance (
    type_id INTEGER PRIMARY KEY,
    default_cycle_strokes INTEGER NOT NULL,
    min_cycle_strokes INTEGER NOT NULL,
    max_cycle_strokes INTEGER NOT NULL,
    recommended_range_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_type_default_maintenance FOREIGN KEY (type_id) REFERENCES mold_functional_types(type_id) ON DELETE CASCADE,
    CONSTRAINT valid_default_cycle CHECK (default_cycle_strokes > 0),
    CONSTRAINT valid_range_order CHECK (min_cycle_strokes <= default_cycle_strokes AND default_cycle_strokes <= max_cycle_strokes),
    CONSTRAINT positive_range_values CHECK (min_cycle_strokes > 0 AND max_cycle_strokes > 0)
);

COMMENT ON TABLE mold_type_default_maintenance IS '模具类型默认保养周期配置表';
COMMENT ON COLUMN mold_type_default_maintenance.default_cycle_strokes IS '推荐的默认保养周期冲次';
COMMENT ON COLUMN mold_type_default_maintenance.min_cycle_strokes IS '最小保养周期冲次';
COMMENT ON COLUMN mold_type_default_maintenance.max_cycle_strokes IS '最大保养周期冲次';

-- 4. 插入模具类型默认保养周期数据
DO $$
BEGIN
    RAISE NOTICE '4. 插入模具类型默认保养周期数据...';
    
    -- 清理可能的重复数据
    DELETE FROM mold_type_default_maintenance;
    
    -- 插入数据，确保所有现有的模具功能类型都有配置
    INSERT INTO mold_type_default_maintenance (
        type_id, default_cycle_strokes, min_cycle_strokes, max_cycle_strokes, recommended_range_description
    )
    SELECT 
        mft.type_id,
        CASE 
            WHEN mft.type_name ILIKE '%落料%' THEN 15000
            WHEN mft.type_name ILIKE '%一引%' OR mft.type_name ILIKE '%1引%' THEN 12000
            WHEN mft.type_name ILIKE '%二引%' OR mft.type_name ILIKE '%2引%' THEN 12000
            WHEN mft.type_name ILIKE '%三引%' OR mft.type_name ILIKE '%3引%' THEN 10000
            WHEN mft.type_name ILIKE '%四引%' OR mft.type_name ILIKE '%4引%' THEN 10000
            WHEN mft.type_name ILIKE '%切边%' THEN 20000
            WHEN mft.type_name ILIKE '%引申%' THEN 12000
            WHEN mft.type_name ILIKE '%成型%' THEN 15000
            ELSE 12000  -- 默认值
        END as default_cycle_strokes,
        CASE 
            WHEN mft.type_name ILIKE '%落料%' THEN 8000
            WHEN mft.type_name ILIKE '%一引%' OR mft.type_name ILIKE '%1引%' THEN 6000
            WHEN mft.type_name ILIKE '%二引%' OR mft.type_name ILIKE '%2引%' THEN 6000
            WHEN mft.type_name ILIKE '%三引%' OR mft.type_name ILIKE '%3引%' THEN 5000
            WHEN mft.type_name ILIKE '%四引%' OR mft.type_name ILIKE '%4引%' THEN 5000
            WHEN mft.type_name ILIKE '%切边%' THEN 10000
            WHEN mft.type_name ILIKE '%引申%' THEN 6000
            WHEN mft.type_name ILIKE '%成型%' THEN 8000
            ELSE 6000  -- 默认最小值
        END as min_cycle_strokes,
        CASE 
            WHEN mft.type_name ILIKE '%落料%' THEN 25000
            WHEN mft.type_name ILIKE '%一引%' OR mft.type_name ILIKE '%1引%' THEN 20000
            WHEN mft.type_name ILIKE '%二引%' OR mft.type_name ILIKE '%2引%' THEN 20000
            WHEN mft.type_name ILIKE '%三引%' OR mft.type_name ILIKE '%3引%' THEN 18000
            WHEN mft.type_name ILIKE '%四引%' OR mft.type_name ILIKE '%4引%' THEN 18000
            WHEN mft.type_name ILIKE '%切边%' THEN 35000
            WHEN mft.type_name ILIKE '%引申%' THEN 20000
            WHEN mft.type_name ILIKE '%成型%' THEN 25000
            ELSE 25000  -- 默认最大值
        END as max_cycle_strokes,
        CASE 
            WHEN mft.type_name ILIKE '%落料%' THEN '落料模工作相对稳定，建议每15000冲次保养一次，重点检查冲裁刃口锋利度和导向精度'
            WHEN mft.type_name ILIKE '%一引%' OR mft.type_name ILIKE '%1引%' THEN '首次引申变形量大，建议每12000冲次保养，重点检查导向装置和冲压面光洁度'
            WHEN mft.type_name ILIKE '%二引%' OR mft.type_name ILIKE '%2引%' THEN '二次引申需要精确控制，建议每12000冲次保养，关注尺寸精度和表面质量'
            WHEN mft.type_name ILIKE '%三引%' OR mft.type_name ILIKE '%3引%' THEN '三次引申工艺复杂，建议每10000冲次保养，重点检查模具各部位磨损'
            WHEN mft.type_name ILIKE '%四引%' OR mft.type_name ILIKE '%4引%' THEN '深度引申对模具要求极高，建议每10000冲次保养，严格控制间隙和润滑'
            WHEN mft.type_name ILIKE '%切边%' THEN '切边模具相对简单，可适当延长至20000冲次，重点检查刃口锋利度和废料清理'
            WHEN mft.type_name ILIKE '%引申%' THEN '引申模具工作强度较大，建议每12000冲次保养，注意润滑和导向'
            WHEN mft.type_name ILIKE '%成型%' THEN '成型模具需要保证精度，建议每15000冲次保养，检查成型面质量'
            ELSE '建议根据模具复杂程度、使用频率和精度要求调整保养周期，定期检查关键部位'
        END as recommended_range_description
    FROM mold_functional_types mft;
    
    RAISE NOTICE '  插入了 % 条模具类型保养周期配置', (SELECT COUNT(*) FROM mold_type_default_maintenance);
END $$;

-- 5. 更新现有模具的保养周期字段
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    RAISE NOTICE '5. 更新现有模具的保养周期数据...';
    
    -- 为空或异常的保养周期设置默认值
    UPDATE molds 
    SET current_maintenance_cycle_strokes = COALESCE(
        (SELECT mtdm.default_cycle_strokes 
         FROM mold_type_default_maintenance mtdm 
         WHERE mtdm.type_id = molds.mold_functional_type_id), 
        12000  -- 兜底默认值
    )
    WHERE current_maintenance_cycle_strokes IS NULL 
       OR current_maintenance_cycle_strokes <= 0;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE '  更新了 % 个模具的保养周期', updated_count;
    
    -- 设置初始保养周期
    UPDATE molds 
    SET initial_maintenance_cycle_strokes = current_maintenance_cycle_strokes
    WHERE initial_maintenance_cycle_strokes IS NULL;
    
    -- 确保累计冲次不为负数
    UPDATE molds 
    SET accumulated_strokes = 0
    WHERE accumulated_strokes IS NULL OR accumulated_strokes < 0;
    
    -- 确保上次保养冲次合理
    UPDATE molds 
    SET last_maintenance_strokes = 0
    WHERE last_maintenance_strokes IS NULL 
       OR last_maintenance_strokes < 0 
       OR last_maintenance_strokes > COALESCE(accumulated_strokes, 0);
    
    RAISE NOTICE '  现有模具数据清理完成';
END $$;

-- 6. 创建索引
DO $$
BEGIN
    RAISE NOTICE '6. 创建性能优化索引...';
END $$;

-- 模具表相关索引
CREATE INDEX IF NOT EXISTS idx_molds_maintenance_cycle 
ON molds(current_maintenance_cycle_strokes) 
WHERE current_maintenance_cycle_strokes > 0;

CREATE INDEX IF NOT EXISTS idx_molds_accumulated_strokes 
ON molds(accumulated_strokes) 
WHERE accumulated_strokes IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_molds_last_maintenance 
ON molds(last_maintenance_strokes) 
WHERE last_maintenance_strokes IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_molds_maintenance_priority 
ON molds(maintenance_priority);

CREATE INDEX IF NOT EXISTS idx_molds_enable_reminder 
ON molds(enable_auto_reminder) 
WHERE enable_auto_reminder = TRUE;

-- 复合索引用于保养提醒查询
CREATE INDEX IF NOT EXISTS idx_molds_maintenance_alert 
ON molds(current_status_id, enable_auto_reminder, current_maintenance_cycle_strokes, accumulated_strokes, last_maintenance_strokes);

-- 历史表索引
CREATE INDEX IF NOT EXISTS idx_maintenance_cycle_history_mold_id 
ON mold_maintenance_cycle_history(mold_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_cycle_history_timestamp 
ON mold_maintenance_cycle_history(adjustment_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_maintenance_cycle_history_user 
ON mold_maintenance_cycle_history(adjusted_by_user_id);

-- 7. 创建保养提醒视图
DO $$
BEGIN
    RAISE NOTICE '7. 创建保养提醒视图...';
END $$;

CREATE OR REPLACE VIEW mold_maintenance_alerts AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    COALESCE(mft.type_name, '未知类型') as functional_type,
    COALESCE(ms.status_name, '未知状态') as current_status,
    COALESCE(sl.location_name, '未知位置') as current_location,
    COALESCE(m.accumulated_strokes, 0) as accumulated_strokes,
    m.current_maintenance_cycle_strokes,
    COALESCE(m.last_maintenance_strokes, 0) as last_maintenance_strokes,
    COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0) as strokes_since_last_maintenance,
    m.current_maintenance_cycle_strokes - (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) as strokes_to_next_maintenance,
    ROUND(
        (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0))::NUMERIC / 
        NULLIF(m.current_maintenance_cycle_strokes, 0) * 100, 
        1
    ) as maintenance_progress_percentage,
    CASE 
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= m.current_maintenance_cycle_strokes 
        THEN 'urgent'
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= 
             (m.current_maintenance_cycle_strokes - COALESCE(m.reminder_advance_strokes, 1000))
        THEN 'warning'
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= 
             (m.current_maintenance_cycle_strokes * 0.8)
        THEN 'info'
        ELSE 'normal'
    END as alert_level,
    COALESCE(m.maintenance_priority, '普通') as maintenance_priority,
    m.enable_auto_reminder,
    m.estimated_maintenance_hours,
    CASE 
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= m.current_maintenance_cycle_strokes 
        THEN 1
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= 
             (m.current_maintenance_cycle_strokes - COALESCE(m.reminder_advance_strokes, 1000))
        THEN 2
        WHEN (COALESCE(m.accumulated_strokes, 0) - COALESCE(m.last_maintenance_strokes, 0)) >= 
             (m.current_maintenance_cycle_strokes * 0.8)
        THEN 3
        ELSE 4
    END as alert_priority_order
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
WHERE m.enable_auto_reminder = TRUE
  AND m.current_maintenance_cycle_strokes > 0
  AND COALESCE(ms.status_name, '') IN ('闲置', '使用中', '已借出', '待保养', '保养中');

COMMENT ON VIEW mold_maintenance_alerts IS '模具保养提醒视图，显示所有需要保养提醒的模具及其状态';

-- 8. 创建存储过程和函数
DO $$
BEGIN
    RAISE NOTICE '8. 创建存储过程和函数...';
END $$;

-- 更新模具保养周期的函数
CREATE OR REPLACE FUNCTION update_mold_maintenance_cycle(
    p_mold_id INTEGER,
    p_new_cycle_strokes INTEGER,
    p_adjustment_reason TEXT,
    p_adjusted_by_user_id INTEGER,
    p_remarks TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_old_cycle_strokes INTEGER;
    v_accumulated_strokes INTEGER;
    v_mold_exists BOOLEAN;
BEGIN
    -- 参数验证
    IF p_mold_id IS NULL OR p_new_cycle_strokes <= 0 OR p_adjusted_by_user_id IS NULL THEN
        RAISE EXCEPTION '参数无效: mold_id=%, new_cycle_strokes=%, user_id=%', 
            p_mold_id, p_new_cycle_strokes, p_adjusted_by_user_id;
    END IF;
    
    -- 检查模具是否存在并获取当前数据
    SELECT 
        current_maintenance_cycle_strokes, 
        COALESCE(accumulated_strokes, 0),
        TRUE
    INTO v_old_cycle_strokes, v_accumulated_strokes, v_mold_exists
    FROM molds 
    WHERE mold_id = p_mold_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION '模具ID % 不存在', p_mold_id;
    END IF;
    
    -- 检查用户是否存在
    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_adjusted_by_user_id) THEN
        RAISE EXCEPTION '用户ID % 不存在', p_adjusted_by_user_id;
    END IF;
    
    -- 更新模具保养周期
    UPDATE molds 
    SET 
        current_maintenance_cycle_strokes = p_new_cycle_strokes,
        maintenance_cycle_adjustment_count = COALESCE(maintenance_cycle_adjustment_count, 0) + 1,
        updated_at = NOW()
    WHERE mold_id = p_mold_id;
    
    -- 记录调整历史
    INSERT INTO mold_maintenance_cycle_history (
        mold_id, old_cycle_strokes, new_cycle_strokes, adjustment_reason,
        adjusted_by_user_id, accumulated_strokes_at_adjustment, remarks
    ) VALUES (
        p_mold_id, v_old_cycle_strokes, p_new_cycle_strokes, p_adjustment_reason,
        p_adjusted_by_user_id, v_accumulated_strokes, p_remarks
    );
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION '更新保养周期失败: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_mold_maintenance_cycle IS '更新模具保养周期并记录调整历史';

-- 记录模具保养完成的函数
CREATE OR REPLACE FUNCTION record_mold_maintenance_completed(
    p_mold_id INTEGER,
    p_maintenance_log_id INTEGER DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_current_strokes INTEGER;
BEGIN
    -- 参数验证
    IF p_mold_id IS NULL THEN
        RAISE EXCEPTION '模具ID不能为空';
    END IF;
    
    -- 获取当前累计冲次
    SELECT COALESCE(accumulated_strokes, 0)
    INTO v_current_strokes
    FROM molds 
    WHERE mold_id = p_mold_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION '模具ID % 不存在', p_mold_id;
    END IF;
    
    -- 更新上次保养冲次
    UPDATE molds 
    SET 
        last_maintenance_strokes = v_current_strokes,
        updated_at = NOW()
    WHERE mold_id = p_mold_id;
    
    -- 可选：如果提供了维修日志ID，可以关联更新
    IF p_maintenance_log_id IS NOT NULL THEN
        -- 这里可以添加与维修日志的关联逻辑
        NULL;
    END IF;
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION '记录保养完成失败: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION record_mold_maintenance_completed IS '记录模具保养完成，更新上次保养时的冲次';

-- 获取保养提醒列表的函数
CREATE OR REPLACE FUNCTION get_mold_maintenance_alerts(
    p_alert_level TEXT DEFAULT 'all',
    p_limit INTEGER DEFAULT 100
) RETURNS TABLE (
    mold_id INTEGER,
    mold_code VARCHAR,
    mold_name VARCHAR,
    functional_type VARCHAR,
    current_status VARCHAR,
    strokes_since_last_maintenance INTEGER,
    strokes_to_next_maintenance INTEGER,
    alert_level TEXT,
    maintenance_priority VARCHAR,
    progress_percentage NUMERIC,
    estimated_hours NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ma.mold_id,
        ma.mold_code,
        ma.mold_name,
        ma.functional_type,
        ma.current_status,
        ma.strokes_since_last_maintenance::INTEGER,
        ma.strokes_to_next_maintenance::INTEGER,
        ma.alert_level,
        ma.maintenance_priority,
        ma.maintenance_progress_percentage,
        ma.estimated_maintenance_hours
    FROM mold_maintenance_alerts ma
    WHERE (p_alert_level = 'all' OR ma.alert_level = p_alert_level)
      AND ma.alert_level != 'normal'
    ORDER BY 
        ma.alert_priority_order,
        CASE ma.maintenance_priority
            WHEN '关键' THEN 1
            WHEN '重要' THEN 2
            WHEN '普通' THEN 3
            ELSE 4
        END,
        ma.strokes_since_last_maintenance DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_mold_maintenance_alerts IS '获取模具保养提醒信息，按优先级和紧急程度排序';

-- 9. 创建触发器（如果相关表存在）
DO $$
BEGIN
    RAISE NOTICE '9. 创建触发器...';
    
    -- 检查mold_usage_records表是否存在
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mold_usage_records') THEN
        
        -- 创建触发器函数
        CREATE OR REPLACE FUNCTION update_mold_accumulated_strokes()
        RETURNS TRIGGER AS $trigger$
        DECLARE
            v_mold_id INTEGER;
        BEGIN
            -- 确定要更新的模具ID
            IF TG_OP = 'DELETE' THEN
                v_mold_id := OLD.mold_id;
            ELSE
                v_mold_id := NEW.mold_id;
            END IF;
            
            -- 更新模具的累计冲次
            UPDATE molds 
            SET 
                accumulated_strokes = (
                    SELECT COALESCE(SUM(strokes_this_session), 0)
                    FROM mold_usage_records 
                    WHERE mold_id = v_mold_id
                      AND strokes_this_session > 0
                ),
                updated_at = NOW()
            WHERE mold_id = v_mold_id;
            
            -- 返回适当的记录
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $trigger$ LANGUAGE plpgsql;
        
        -- 删除现有触发器（如果存在）
        DROP TRIGGER IF EXISTS trigger_update_accumulated_strokes ON mold_usage_records;
        
        -- 创建新触发器
        CREATE TRIGGER trigger_update_accumulated_strokes
            AFTER INSERT OR UPDATE OR DELETE ON mold_usage_records
            FOR EACH ROW
            EXECUTE FUNCTION update_mold_accumulated_strokes();
            
        RAISE NOTICE '  创建了mold_usage_records触发器';
    ELSE
        RAISE NOTICE '  mold_usage_records表不存在，跳过触发器创建';
    END IF;
END $$;

-- 10. 创建统计视图
DO $$
BEGIN
    RAISE NOTICE '10. 创建统计分析视图...';
END $$;

CREATE OR REPLACE VIEW mold_maintenance_cycle_statistics AS
SELECT 
    COALESCE(mft.type_name, '未知类型') as functional_type,
    COUNT(*) as total_molds,
    ROUND(AVG(m.current_maintenance_cycle_strokes), 0) as avg_cycle_strokes,
    MIN(m.current_maintenance_cycle_strokes) as min_cycle_strokes,
    MAX(m.current_maintenance_cycle_strokes) as max_cycle_strokes,
    ROUND(AVG(COALESCE(m.accumulated_strokes, 0)), 0) as avg_accumulated_strokes,
    COUNT(CASE WHEN ma.alert_level = 'urgent' THEN 1 END) as urgent_count,
    COUNT(CASE WHEN ma.alert_level = 'warning' THEN 1 END) as warning_count,
    COUNT(CASE WHEN ma.alert_level = 'info' THEN 1 END) as info_count,
    COUNT(CASE WHEN m.maintenance_priority = '关键' THEN 1 END) as critical_priority_count,
    COUNT(CASE WHEN m.maintenance_priority = '重要' THEN 1 END) as important_priority_count,
    ROUND(AVG(m.estimated_maintenance_hours), 1) as avg_estimated_hours
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_maintenance_alerts ma ON m.mold_id = ma.mold_id
WHERE m.current_maintenance_cycle_strokes > 0
GROUP BY mft.type_name
ORDER BY total_molds DESC;

COMMENT ON VIEW mold_maintenance_cycle_statistics IS '按模具类型统计保养周期和提醒情况';

-- 11. 为现有模具创建初始化历史记录
DO $$
DECLARE
    inserted_count INTEGER;
BEGIN
    RAISE NOTICE '11. 创建现有模具的初始化历史记录...';
    
    INSERT INTO mold_maintenance_cycle_history (
        mold_id, old_cycle_strokes, new_cycle_strokes, adjustment_reason,
        adjusted_by_user_id, accumulated_strokes_at_adjustment, remarks
    )
    SELECT 
        m.mold_id,
        NULL as old_cycle_strokes,
        m.current_maintenance_cycle_strokes,
        '系统初始化 - 数据库升级时设置' as adjustment_reason,
        COALESCE((SELECT user_id FROM users WHERE role_id = 1 LIMIT 1), 1) as adjusted_by_user_id,
        COALESCE(m.accumulated_strokes, 0) as accumulated_strokes_at_adjustment,
        CONCAT('模具类型: ', COALESCE(mft.type_name, '未知'), 
               ', 初始保养周期: ', m.current_maintenance_cycle_strokes, ' 冲次') as remarks
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    WHERE NOT EXISTS (
        SELECT 1 FROM mold_maintenance_cycle_history h 
        WHERE h.mold_id = m.mold_id
    );
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE '  为 % 个现有模具创建了初始化记录', inserted_count;
END $$;

-- 12. 数据验证和完整性检查
DO $$
DECLARE
    error_count INTEGER;
    warning_count INTEGER;
BEGIN
    RAISE NOTICE '12. 执行数据验证和完整性检查...';
    
    -- 检查保养周期异常数据
    SELECT COUNT(*) INTO error_count
    FROM molds 
    WHERE current_maintenance_cycle_strokes <= 0;
    
    IF error_count > 0 THEN
        RAISE WARNING '发现 % 个模具的保养周期 <= 0，需要修复', error_count;
        
        UPDATE molds 
        SET current_maintenance_cycle_strokes = 12000
        WHERE current_maintenance_cycle_strokes <= 0;
    END IF;
    
    -- 检查累计冲次异常数据
    SELECT COUNT(*) INTO warning_count
    FROM molds 
    WHERE accumulated_strokes < 0;
    
    IF warning_count > 0 THEN
        RAISE WARNING '发现 % 个模具的累计冲次 < 0，将重置为0', warning_count;
        
        UPDATE molds 
        SET accumulated_strokes = 0
        WHERE accumulated_strokes < 0;
    END IF;
    
    -- 检查上次保养冲次逻辑错误
    SELECT COUNT(*) INTO warning_count
    FROM molds 
    WHERE last_maintenance_strokes > COALESCE(accumulated_strokes, 0);
    
    IF warning_count > 0 THEN
        RAISE WARNING '发现 % 个模具的上次保养冲次 > 累计冲次，将重置', warning_count;
        
        UPDATE molds 
        SET last_maintenance_strokes = 0
        WHERE last_maintenance_strokes > COALESCE(accumulated_strokes, 0);
    END IF;
    
    -- 验证外键关系
    SELECT COUNT(*) INTO error_count
    FROM molds m
    LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
    WHERE m.mold_functional_type_id IS NOT NULL AND mft.type_id IS NULL;
    
    IF error_count > 0 THEN
        RAISE WARNING '发现 % 个模具的功能类型ID无效', error_count;
    END IF;
    
    RAISE NOTICE '  数据验证完成，修复了 % 个错误，% 个警告', error_count, warning_count;
END $$;

-- 13. 设置权限（示例，实际部署时根据具体角色调整）
DO $$
BEGIN
    RAISE NOTICE '13. 设置数据访问权限...';
    
    -- 为所有用户授予查看保养提醒的权限
    GRANT SELECT ON mold_maintenance_alerts TO PUBLIC;
    GRANT SELECT ON mold_maintenance_cycle_statistics TO PUBLIC;
    GRANT SELECT ON mold_type_default_maintenance TO PUBLIC;
    
    -- 为所有用户授予查看历史记录的权限
    GRANT SELECT ON mold_maintenance_cycle_history TO PUBLIC;
    
    -- 执行函数的权限（实际环境中应该限制给特定角色）
    -- GRANT EXECUTE ON FUNCTION update_mold_maintenance_cycle TO role_admin;
    -- GRANT EXECUTE ON FUNCTION record_mold_maintenance_completed TO role_admin, role_technician;
    
    RAISE NOTICE '  权限设置完成';
END $$;

-- 提交事务
COMMIT;

-- 执行完成消息
DO $$
DECLARE
    total_molds INTEGER;
    total_alerts INTEGER;
    total_types INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_molds FROM molds WHERE current_maintenance_cycle_strokes > 0;
    SELECT COUNT(*) INTO total_alerts FROM mold_maintenance_alerts WHERE alert_level != 'normal';
    SELECT COUNT(*) INTO total_types FROM mold_type_default_maintenance;
    
    RAISE NOTICE '=================================================';
    RAISE NOTICE '🎉 保养周期管理数据库更新完成！';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '📊 统计信息:';
    RAISE NOTICE '  - 配置了保养周期的模具: % 个', total_molds;
    RAISE NOTICE '  - 当前需要关注的模具: % 个', total_alerts;
    RAISE NOTICE '  - 模具类型配置: % 种', total_types;
    RAISE NOTICE '=================================================';
    RAISE NOTICE '🔧 新增功能:';
    RAISE NOTICE '  ✅ 保养周期设置和历史记录跟踪';
    RAISE NOTICE '  ✅ 智能保养提醒系统（多级别提醒）';
    RAISE NOTICE '  ✅ 模具类型默认保养周期配置';
    RAISE NOTICE '  ✅ 保养周期统计和分析视图';
    RAISE NOTICE '  ✅ 自动冲次累计和提醒计算';
    RAISE NOTICE '  ✅ 完整的数据验证和错误修复';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '📋 使用方法:';
    RAISE NOTICE '  🔍 查看保养提醒: SELECT * FROM mold_maintenance_alerts;';
    RAISE NOTICE '  🔄 更新保养周期: SELECT update_mold_maintenance_cycle(...);';
    RAISE NOTICE '  ✅ 记录保养完成: SELECT record_mold_maintenance_completed(...);';
    RAISE NOTICE '  📈 获取提醒列表: SELECT * FROM get_mold_maintenance_alerts();';
    RAISE NOTICE '  📊 查看统计信息: SELECT * FROM mold_maintenance_cycle_statistics;';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '⚠️  重要提醒:';
    RAISE NOTICE '  - 请在应用程序中测试所有新功能';
    RAISE NOTICE '  - 建议为用户提供保养周期设置培训';
    RAISE NOTICE '  - 定期检查和优化保养周期设置';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '完成时间: %', NOW();
END $$;