-- 修复借用状态数据脚本
-- 解决"无法找到状态 '已借出'"等错误;

-- 1. 检查当前loan_statuses表中的数据
SELECT 'Current loan_statuses data:' as info;
SELECT status_id, status_name FROM loan_statuses ORDER BY status_id;

-- 2. 检查是否缺少必要的状态
SELECT 'Missing statuses check:' as info;
WITH required_statuses AS (
    SELECT unnest(ARRAY['待审批', '已批准', '已批准待借出', '已借出', '已归还', '已驳回', '逾期', '外借申请中']) as status_name
)
SELECT r.status_name as missing_status
FROM required_statuses r
LEFT JOIN loan_statuses ls ON r.status_name = ls.status_name
WHERE ls.status_name IS NULL;

-- 3. 删除并重新插入正确的借用状态数据
DELETE FROM loan_statuses;

-- 重新插入完整的借用状态数据
INSERT INTO loan_statuses (status_name, description) VALUES 
('待审批', '申请已提交，等待审批'),
('已批准', '申请已批准，等待处理'),
('已批准待借出', '申请已批准，等待借出'),
('已借出', '模具已借出使用'),
('已归还', '模具已归还'),
('已驳回', '申请被驳回'),
('逾期', '超过预期归还时间'),
('外借申请中', '申请处理中，模具预留状态')
ON CONFLICT (status_name) DO UPDATE SET 
    description = EXCLUDED.description;

-- 4. 检查mold_statuses表是否有对应的模具状态
SELECT 'Current mold_statuses data:' as info;
SELECT status_id, status_name FROM mold_statuses ORDER BY status_id;

-- 检查并添加缺少的模具状态
INSERT INTO mold_statuses (status_name, description) VALUES 
('外借申请中', '模具正在处理借用申请'),
('已预定', '模具已预定待借出'),
('已借出', '模具已借出使用')
ON CONFLICT (status_name) DO UPDATE SET 
    description = EXCLUDED.description;

-- 5. 验证状态数据完整性
SELECT 'Final verification - Loan statuses:' as info;
SELECT status_id, status_name, description FROM loan_statuses ORDER BY status_id;

SELECT 'Final verification - Mold statuses:' as info;
SELECT status_id, status_name, description FROM mold_statuses ORDER BY status_id;

-- 6. 检查是否有孤立的借用记录
SELECT 'Orphaned loan records check:' as info;
SELECT COUNT(*) as orphaned_count
FROM mold_loan_records mlr
LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
WHERE ls.status_id IS NULL;

-- 7. 如果有孤立记录，显示详情
SELECT 'Orphaned loan records details:' as info;
SELECT mlr.loan_id, mlr.loan_status_id, mlr.mold_id
FROM mold_loan_records mlr
LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
WHERE ls.status_id IS NULL
LIMIT 5;