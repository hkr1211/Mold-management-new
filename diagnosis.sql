-- 借用状态诊断脚本
-- 在PostgreSQL中执行此脚本来诊断问题

\echo '=== 借用状态诊断报告 ==='
\echo ''

-- 1. 检查所有借用状态
\echo '1. 当前借用状态列表:'
SELECT status_id, status_name, description FROM loan_statuses ORDER BY status_id;

\echo ''

-- 2. 检查所有模具状态
\echo '2. 当前模具状态列表:'
SELECT status_id, status_name, description FROM mold_statuses ORDER BY status_id;

\echo ''

-- 3. 检查借用记录
\echo '3. 当前借用记录状态:'
SELECT 
    mlr.loan_id,
    mlr.loan_status_id,
    ls.status_name as loan_status,
    mlr.mold_id,
    m.mold_code,
    m.current_status_id,
    ms.status_name as mold_status
FROM mold_loan_records mlr
LEFT JOIN loan_statuses ls ON mlr.loan_status_id = ls.status_id
LEFT JOIN molds m ON mlr.mold_id = m.mold_id
LEFT JOIN mold_statuses ms ON m.current_status_id = ms.status_id
ORDER BY mlr.loan_id;

\echo ''

-- 4. 检查孤立记录
\echo '4. 孤立的借用记录 (状态ID无效):'
SELECT 
    mlr.loan_id,
    mlr.loan_status_id as invalid_status_id,
    'loan_status_id指向不存在的状态' as issue
FROM mold_loan_records mlr
WHERE mlr.loan_status_id NOT IN (SELECT status_id FROM loan_statuses);

\echo ''

-- 5. 检查孤立的模具
\echo '5. 模具状态问题:'
SELECT 
    m.mold_id,
    m.mold_code,
    m.current_status_id,
    'mold status_id指向不存在的状态' as issue
FROM molds m
WHERE m.current_status_id NOT IN (SELECT status_id FROM mold_statuses);

\echo ''

-- 6. 状态名称精确匹配检查
\echo '6. 关键状态检查:'
SELECT 
    CASE 
        WHEN EXISTS(SELECT 1 FROM loan_statuses WHERE status_name = '已借出') 
        THEN '✓ loan_statuses 中存在 "已借出"'
        ELSE '✗ loan_statuses 中缺少 "已借出"'
    END as loan_status_check
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS(SELECT 1 FROM mold_statuses WHERE status_name = '已借出') 
        THEN '✓ mold_statuses 中存在 "已借出"'
        ELSE '✗ mold_statuses 中缺少 "已借出"'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS(SELECT 1 FROM loan_statuses WHERE status_name = '已批准') 
        THEN '✓ loan_statuses 中存在 "已批准"'
        ELSE '✗ loan_statuses 中缺少 "已批准"'
    END;

\echo ''
\echo '=== 诊断完成 ==='
\echo ''
\echo '修复建议:'
\echo '1. 如果发现孤立记录，运行修复脚本'
\echo '2. 如果缺少关键状态，重新插入状态数据'
\echo '3. 修复后重启Streamlit应用'