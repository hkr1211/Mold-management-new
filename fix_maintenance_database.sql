-- 维修保养模块数据库结构修复和扩展脚本
-- fix_maintenance_database.sql

-- 1. 确保 mold_maintenance_logs 表结构完整
DO $$
BEGIN
    -- 检查并添加缺失的字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'mold_maintenance_logs' AND column_name = 'replaced_parts_info') THEN
        ALTER TABLE mold_maintenance_logs ADD COLUMN replaced_parts_info JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'mold_maintenance_logs' AND column_name = 'maintenance_cost') THEN
        ALTER TABLE mold_maintenance_logs ADD COLUMN maintenance_cost DECIMAL(10,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'molds' AND column_name = 'last_maintenance_date') THEN
        ALTER TABLE molds ADD COLUMN last_maintenance_date DATE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'molds' AND column_name = 'maintenance_alerts_enabled') THEN
        ALTER TABLE molds ADD COLUMN maintenance_alerts_enabled BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- 2. 确保维修保养类型数据完整
INSERT INTO maintenance_types (type_name, is_repair, description) VALUES 
('日常保养', FALSE, '日常清洁和基础维护'),
('定期保养', FALSE, '按周期进行的全面保养'),
('预防性保养', FALSE, '预防性维护检查'),
('故障维修', TRUE, '设备故障后的修复工作'),
('精度维修', TRUE, '提高模具精度的维修'),
('改进升级', TRUE, '模具性能改进和升级'),
('紧急维修', TRUE, '紧急故障抢修'),
('外协维修', TRUE, '委托外部专业机构维修')
ON CONFLICT (type_name) DO NOTHING;

-- 3. 确保维修结果状态数据完整
INSERT INTO maintenance_result_statuses (status_name, description) VALUES 
('进行中', '维修保养工作正在进行'),
('暂停', '维修保养工作暂时停止'),
('完成待检', '维修保养完成，等待质量检验'),
('合格可用', '检验合格，可以正常使用'),
('失败待查', '维修失败，需要进一步分析'),
('等待备件', '等待备件到货后继续'),
('需要外协', '需要外部专业机构协助'),
('已取消', '维修保养任务被取消'),
('待开始', '任务已创建，等待开始执行')
ON CONFLICT (status_name) DO NOTHING;

-- 4. 确保模具状态支持维修保养流程
INSERT INTO mold_statuses (status_name, description) VALUES 
('维修中', '模具正在进行维修'),
('保养中', '模具正在进行保养'),
('待维修', '模具等待维修'),
('待保养', '模具等待保养'),
('检验中', '维修保养后正在检验'),
('维修失败', '维修失败，不可使用')
ON CONFLICT (status_name) DO NOTHING;

-- 5. 创建维修保养相关的视图，便于查询
CREATE OR REPLACE VIEW v_maintenance_alerts AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    m.accumulated_strokes,
    m.maintenance_cycle_strokes,
    m.theoretical_lifespan_strokes,
    mft.type_name as functional_type,
    ms.status_name as current_status,
    sl.location_name as current_location,
    CASE 
        WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes 
        THEN '需要保养'
        WHEN m.current_status_id IN (SELECT status_id FROM mold_statuses WHERE status_name IN ('待维修', '待保养'))
        THEN '等待维修/保养'
        WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9
        THEN '即将到期'
        WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.8
        THEN '注意寿命'
        ELSE '正常'
    END as maintenance_status,
    CASE 
        WHEN m.maintenance_cycle_strokes > 0 
        THEN m.accumulated_strokes - (m.accumulated_strokes / m.maintenance_cycle_strokes) * m.maintenance_cycle_strokes
        ELSE 0
    END as strokes_since_maintenance,
    CASE 
        WHEN m.theoretical_lifespan_strokes > 0 
        THEN m.theoretical_lifespan_strokes - m.accumulated_strokes
        ELSE NULL
    END as remaining_lifespan
FROM molds m
LEFT JOIN mold_functional_types mft ON m.mold_functional_type_id = mft.type_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
LEFT JOIN storage_locations sl ON m.current_location_id = sl.location_id
WHERE m.maintenance_alerts_enabled = TRUE;

-- 6. 创建维修保养统计视图
CREATE OR REPLACE VIEW v_maintenance_statistics AS
SELECT 
    m.mold_id,
    m.mold_code,
    m.mold_name,
    COUNT(mml.log_id) as total_maintenance_count,
    COUNT(CASE WHEN mt.is_repair = TRUE THEN 1 END) as repair_count,
    COUNT(CASE WHEN mt.is_repair = FALSE THEN 1 END) as maintenance_count,
    COALESCE(SUM(mml.maintenance_cost), 0) as total_maintenance_cost,
    COALESCE(AVG(mml.maintenance_cost), 0) as avg_maintenance_cost,
    MAX(mml.maintenance_start_timestamp) as last_maintenance_date,
    CASE 
        WHEN COUNT(mml.log_id) = 0 THEN '无记录'
        WHEN COUNT(mml.log_id) <= 2 THEN '维护较少'
        WHEN COUNT(mml.log_id) <= 5 THEN '维护正常'
        ELSE '维护频繁'
    END as maintenance_frequency_level
FROM molds m
LEFT JOIN mold_maintenance_logs mml ON m.mold_id = mml.mold_id
LEFT JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
GROUP BY m.mold_id, m.mold_code, m.mold_name;

-- 7. 创建优化索引
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_start_time ON mold_maintenance_logs(maintenance_start_timestamp);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_mold_type ON mold_maintenance_logs(mold_id, maintenance_type_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_maintained_by ON mold_maintenance_logs(maintained_by_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_result_status ON mold_maintenance_logs(result_status_id);
CREATE INDEX IF NOT EXISTS idx_molds_accumulated_strokes ON molds(accumulated_strokes);
CREATE INDEX IF NOT EXISTS idx_molds_maintenance_cycle ON molds(maintenance_cycle_strokes);

-- 8. 创建维修保养提醒函数
CREATE OR REPLACE FUNCTION get_maintenance_alerts(
    p_alert_type VARCHAR(20) DEFAULT 'all' -- 'overdue', 'warning', 'urgent', 'all'
)
RETURNS TABLE (
    mold_id INTEGER,
    mold_code VARCHAR(100),
    mold_name VARCHAR(255),
    alert_type VARCHAR(20),
    alert_priority INTEGER,
    alert_message TEXT,
    strokes_over_limit INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.mold_id,
        m.mold_code,
        m.mold_name,
        CASE 
            WHEN ms.status_name IN ('待维修', '待保养') THEN 'urgent'
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes THEN 'overdue'
            WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9 THEN 'warning'
            ELSE 'normal'
        END::VARCHAR(20) as alert_type,
        CASE 
            WHEN ms.status_name IN ('待维修', '待保养') THEN 1
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes THEN 2
            WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9 THEN 3
            ELSE 9
        END as alert_priority,
        CASE 
            WHEN ms.status_name = '待维修' THEN '模具需要紧急维修'
            WHEN ms.status_name = '待保养' THEN '模具需要紧急保养'
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes 
            THEN FORMAT('保养超期 %s 冲次', m.accumulated_strokes - m.maintenance_cycle_strokes)
            WHEN m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9 
            THEN FORMAT('寿命即将到期，剩余 %s 冲次', m.theoretical_lifespan_strokes - m.accumulated_strokes)
            ELSE '状态正常'
        END as alert_message,
        CASE 
            WHEN m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes 
            THEN m.accumulated_strokes - m.maintenance_cycle_strokes
            ELSE 0
        END as strokes_over_limit
    FROM molds m
    LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
    WHERE 
        (p_alert_type = 'all' OR 
         (p_alert_type = 'urgent' AND ms.status_name IN ('待维修', '待保养')) OR
         (p_alert_type = 'overdue' AND m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes) OR
         (p_alert_type = 'warning' AND m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9))
        AND (p_alert_type = 'all' OR 
             (p_alert_type != 'all' AND 
              (ms.status_name IN ('待维修', '待保养') OR
               (m.maintenance_cycle_strokes > 0 AND m.accumulated_strokes >= m.maintenance_cycle_strokes) OR
               (m.theoretical_lifespan_strokes > 0 AND m.accumulated_strokes >= m.theoretical_lifespan_strokes * 0.9))))
    ORDER BY alert_priority, m.mold_code;
END $$;

-- 9. 创建维修保养记录汇总函数
CREATE OR REPLACE FUNCTION get_maintenance_summary(
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    summary_type VARCHAR(50),
    record_count BIGINT,
    total_cost NUMERIC,
    avg_cost NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        '总计'::VARCHAR(50) as summary_type,
        COUNT(*) as record_count,
        COALESCE(SUM(mml.maintenance_cost), 0) as total_cost,
        COALESCE(AVG(mml.maintenance_cost), 0) as avg_cost
    FROM mold_maintenance_logs mml
    WHERE mml.maintenance_start_timestamp::DATE BETWEEN p_start_date AND p_end_date
    
    UNION ALL
    
    SELECT 
        CASE WHEN mt.is_repair THEN '维修' ELSE '保养' END::VARCHAR(50) as summary_type,
        COUNT(*) as record_count,
        COALESCE(SUM(mml.maintenance_cost), 0) as total_cost,
        COALESCE(AVG(mml.maintenance_cost), 0) as avg_cost
    FROM mold_maintenance_logs mml
    JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
    WHERE mml.maintenance_start_timestamp::DATE BETWEEN p_start_date AND p_end_date
    GROUP BY mt.is_repair
    
    UNION ALL
    
    SELECT 
        mt.type_name::VARCHAR(50) as summary_type,
        COUNT(*) as record_count,
        COALESCE(SUM(mml.maintenance_cost), 0) as total_cost,
        COALESCE(AVG(mml.maintenance_cost), 0) as avg_cost
    FROM mold_maintenance_logs mml
    JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
    WHERE mml.maintenance_start_timestamp::DATE BETWEEN p_start_date AND p_end_date
    GROUP BY mt.type_name, mt.type_id
    ORDER BY record_count DESC;
END $$;

-- 10. 创建模具维修历史触发器，自动更新模具的最后维修日期
CREATE OR REPLACE FUNCTION update_mold_last_maintenance()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果维修保养完成，更新模具的最后维修日期
    IF NEW.maintenance_end_timestamp IS NOT NULL AND 
       NEW.result_status_id IN (SELECT status_id FROM maintenance_result_statuses 
                               WHERE status_name IN ('合格可用', '完成待检')) THEN
        UPDATE molds 
        SET last_maintenance_date = NEW.maintenance_end_timestamp::DATE
        WHERE mold_id = NEW.mold_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trigger_update_mold_last_maintenance ON mold_maintenance_logs;
CREATE TRIGGER trigger_update_mold_last_maintenance
    AFTER INSERT OR UPDATE ON mold_maintenance_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_mold_last_maintenance();

-- 11. 创建维修保养工作量统计视图（按技术人员）
CREATE OR REPLACE VIEW v_technician_workload AS
SELECT 
    u.user_id,
    u.full_name as technician_name,
    COUNT(mml.log_id) as total_tasks,
    COUNT(CASE WHEN mml.maintenance_end_timestamp IS NULL THEN 1 END) as ongoing_tasks,
    COUNT(CASE WHEN mt.is_repair = TRUE THEN 1 END) as repair_tasks,
    COUNT(CASE WHEN mt.is_repair = FALSE THEN 1 END) as maintenance_tasks,
    COALESCE(SUM(mml.maintenance_cost), 0) as total_cost_handled,
    COALESCE(AVG(
        CASE WHEN mml.maintenance_end_timestamp IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (mml.maintenance_end_timestamp - mml.maintenance_start_timestamp))/3600 
        END
    ), 0) as avg_task_hours
FROM users u
JOIN roles r ON u.role_id = r.role_id
LEFT JOIN mold_maintenance_logs mml ON u.user_id = mml.maintained_by_id
LEFT JOIN maintenance_types mt ON mml.maintenance_type_id = mt.type_id
WHERE r.role_name = '模具工' AND u.is_active = TRUE
GROUP BY u.user_id, u.full_name;

-- 12. 插入一些示例数据（如果表为空）
DO $$
DECLARE
    mold_count INTEGER;
    maintenance_count INTEGER;
BEGIN
    -- 检查是否有模具数据
    SELECT COUNT(*) INTO mold_count FROM molds;
    
    -- 检查是否有维修记录
    SELECT COUNT(*) INTO maintenance_count FROM mold_maintenance_logs;
    
    -- 如果有模具但没有维修记录，插入一些示例记录
    IF mold_count > 0 AND maintenance_count = 0 THEN
        -- 插入一些历史维修记录
        INSERT INTO mold_maintenance_logs (
            mold_id, maintenance_type_id, maintained_by_id,
            maintenance_start_timestamp, maintenance_end_timestamp,
            problem_description, actions_taken, maintenance_cost,
            result_status_id, notes
        )
        SELECT 
            m.mold_id,
            mt.type_id,
            u.user_id,
            CURRENT_TIMESTAMP - INTERVAL '30 days' + (random() * INTERVAL '25 days'),
            CURRENT_TIMESTAMP - INTERVAL '30 days' + (random() * INTERVAL '25 days') + INTERVAL '2 hours',
            '定期保养检查',
            '清洁模具表面，检查各部件，润滑关键部位',
            50.00 + random() * 200,
            mrs.status_id,
            '保养完成，状态良好'
        FROM molds m
        CROSS JOIN (SELECT type_id FROM maintenance_types WHERE type_name = '定期保养' LIMIT 1) mt
        CROSS JOIN (SELECT user_id FROM users u JOIN roles r ON u.role_id = r.role_id 
                   WHERE r.role_name = '模具工' AND u.is_active = TRUE LIMIT 1) u
        CROSS JOIN (SELECT status_id FROM maintenance_result_statuses WHERE status_name = '合格可用' LIMIT 1) mrs
        WHERE random() < 0.3  -- 只为30%的模具创建历史记录
        LIMIT 10;
    END IF;
END $$;

-- 13. 创建权限和安全设置
-- 确保模具工只能查看和更新自己负责的维修记录
CREATE OR REPLACE FUNCTION check_maintenance_access(user_id INTEGER, log_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR(50);
    record_owner INTEGER;
BEGIN
    -- 获取用户角色
    SELECT r.role_name INTO user_role
    FROM users u
    JOIN roles r ON u.role_id = r.role_id
    WHERE u.user_id = check_maintenance_access.user_id;
    
    -- 管理员和超级管理员有全部权限
    IF user_role IN ('超级管理员', '模具库管理员') THEN
        RETURN TRUE;
    END IF;
    
    -- 模具工只能访问自己的记录
    IF user_role = '模具工' THEN
        SELECT maintained_by_id INTO record_owner
        FROM mold_maintenance_logs
        WHERE mold_maintenance_logs.log_id = check_maintenance_access.log_id;
        
        RETURN (record_owner = check_maintenance_access.user_id);
    END IF;
    
    -- 其他情况拒绝访问
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 14. 最后的数据一致性检查和修复
UPDATE molds 
SET last_maintenance_date = (
    SELECT MAX(mml.maintenance_end_timestamp::DATE)
    FROM mold_maintenance_logs mml
    WHERE mml.mold_id = molds.mold_id 
    AND mml.maintenance_end_timestamp IS NOT NULL
)
WHERE last_maintenance_date IS NULL;

-- 15. 输出安装完成信息
DO $$
BEGIN
    RAISE NOTICE '维修保养模块数据库结构安装完成！';
    RAISE NOTICE '- 已创建/更新必要的表字段';
    RAISE NOTICE '- 已插入基础数据';
    RAISE NOTICE '- 已创建优化视图和函数';
    RAISE NOTICE '- 已设置索引和触发器';
    RAISE NOTICE '系统已准备就绪，可以开始使用维修保养功能。';
END $$;