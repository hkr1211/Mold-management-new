-- 插入基础数据

-- 角色数据
INSERT INTO roles (role_name, description) VALUES
('超级管理员', '系统超级管理员，拥有所有权限'),
('模具库管理员', '负责模具台账、借用管理等'),
('模具工', '负责模具维修保养'),
('冲压操作工', '负责模具借用和使用')
ON CONFLICT (role_name) DO NOTHING;

-- 默认用户（密码为 admin123）
INSERT INTO users (username, password_hash, full_name, role_id, email) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyZhL.Ycw.4OV6', '系统管理员', 1, 'admin@company.com'),
('warehouse_mgr', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyZhL.Ycw.4OV6', '库管员', 2, 'warehouse@company.com'),
('technician1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyZhL.Ycw.4OV6', '模具工张师傅', 3, 'tech1@company.com'),
('operator1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyZhL.Ycw.4OV6', '操作工李师傅', 4, 'op1@company.com')
ON CONFLICT (username) DO NOTHING;

-- 模具功能类型
INSERT INTO mold_functional_types (type_name, description) VALUES
('落料模', '用于金属片材的落料成型'),
('一引模', '第一次拉伸成型模具'),
('二引模', '第二次拉伸成型模具'),
('三引模', '第三次拉伸成型模具'),
('四引模', '第四次拉伸成型模具'),
('切边模', '用于产品切边整形')
ON CONFLICT (type_name) DO NOTHING;

-- 模具状态
INSERT INTO mold_statuses (status_name, description) VALUES
('闲置', '模具空闲可用状态'),
('使用中', '模具正在生产中'),
('已借出', '模具已被借用'),
('维修中', '模具正在维修'),
('保养中', '模具正在保养'),
('待维修', '模具需要维修'),
('待保养', '模具需要保养'),
('报废', '模具已报废')
ON CONFLICT (status_name) DO NOTHING;

-- 存放位置
INSERT INTO storage_locations (location_name, description) VALUES
('A区-01架', 'A区第1号货架'),
('A区-02架', 'A区第2号货架'),
('A区-03架', 'A区第3号货架'),
('B区-01架', 'B区第1号货架'),
('B区-02架', 'B区第2号货架'),
('B区-03架', 'B区第3号货架'),
('维修车间', '模具维修车间'),
('生产车间', '生产现场')
ON CONFLICT (location_name) DO NOTHING;

-- 模具部件分类
INSERT INTO mold_part_categories (category_name, description) VALUES
('模架', '模具架体结构'),
('上模', '模具上半部分'),
('下模', '模具下半部分'),
('芯子', '模具成型芯子'),
('压边圈', '控制材料流动的压边圈')
ON CONFLICT (category_name) DO NOTHING;

-- 产品类型
INSERT INTO product_types (type_name, description) VALUES
('平底圆杯', '平底圆形杯状产品'),
('异形杯', '异形杯状产品'),
('金属圆片', '圆形片状产品')
ON CONFLICT (type_name) DO NOTHING;

-- 金属材料
INSERT INTO materials (material_name, description) VALUES
('钛', '钛金属材料'),
('钼', '钼金属材料'),
('锆', '锆金属材料'),
('铌', '铌金属材料'),
('钽', '钽金属材料'),
('钴', '钴金属材料'),
('铜', '铜金属材料'),
('铁', '铁金属材料')
ON CONFLICT (material_name) DO NOTHING;

-- 借用状态
INSERT INTO loan_statuses (status_name, description) VALUES
('待审批', '借用申请等待审批'),
('已批准', '借用申请已批准'),
('已领用', '模具已领用'),
('已归还', '模具已归还'),
('已驳回', '借用申请被驳回'),
('逾期', '模具归还逾期')
ON CONFLICT (status_name) DO NOTHING;

-- 维修保养类型
INSERT INTO maintenance_types (type_name, is_repair, description) VALUES
('日常保养', FALSE, '日常清洁保养'),
('定期保养', FALSE, '定期深度保养'),
('故障维修', TRUE, '故障修理'),
('预防性维修', TRUE, '预防性维修'),
('改进升级', TRUE, '模具改进升级')
ON CONFLICT (type_name) DO NOTHING;

-- 维修保养结果状态
INSERT INTO maintenance_result_statuses (status_name, description) VALUES
('完成待检', '维修保养完成，等待检验'),
('合格可用', '检验合格，可以使用'),
('失败待查', '维修失败，需要进一步检查'),
('等待备件', '等待备件到货'),
('报废处理', '无法修复，建议报废')
ON CONFLICT (status_name) DO NOTHING;

-- 示例模具数据
INSERT INTO molds (
    mold_code, mold_name, mold_functional_type_id, 
    current_status_id, current_location_id, responsible_person_id,
    theoretical_lifespan_strokes, maintenance_cycle_strokes,
    supplier, entry_date
) VALUES
('MD001', 'Φ50钛平底杯落料模', 1, 1, 1, 2, 100000, 5000, '模具工张师傅', CURRENT_DATE),
('MD002', 'Φ50钛平底杯一引模', 2, 1, 1, 2, 80000, 4000, '模具工张师