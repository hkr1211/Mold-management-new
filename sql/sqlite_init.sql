-- sql/sqlite_init.sql — SQLite 数据库初始化（建表 + 基础数据）
-- 所有 CREATE TABLE 使用 IF NOT EXISTS，幂等安全。
--
-- ⚠️ 本文件是数据库 schema 的【唯一事实来源】(single source of truth)。
--    运行时由 app/utils/database.py::initialize_database() 执行。
--    历史的 PostgreSQL Alembic 迁移与 SQLAlchemy 模型 (models.py) 已移除。
--    任何表结构变更都应先改本文件。

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── 角色表 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT    NOT NULL UNIQUE,
    description TEXT
);

-- ── 用户表 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    email         TEXT,
    role_id       INTEGER REFERENCES roles(role_id),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    DEFAULT (datetime('now')),
    updated_at    TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);

-- ── 模具功能类型字典 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_functional_types (
    type_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name   TEXT    NOT NULL UNIQUE,
    description TEXT
);

-- ── 模具状态字典 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_statuses (
    status_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT    NOT NULL UNIQUE,
    description TEXT
);

-- ── 存放位置字典 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS storage_locations (
    location_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name TEXT    NOT NULL UNIQUE,
    description   TEXT
);

-- ── 模具主数据 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS molds (
    mold_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_code                   TEXT    NOT NULL UNIQUE,
    mold_name                   TEXT    NOT NULL,
    mold_drawing_number         TEXT,
    mold_functional_type_id     INTEGER REFERENCES mold_functional_types(type_id),
    supplier                    TEXT,
    manufacturing_date          TEXT,
    theoretical_lifespan_strokes INTEGER,
    accumulated_strokes         INTEGER DEFAULT 0,
    maintenance_cycle_strokes   INTEGER,
    current_status_id           INTEGER REFERENCES mold_statuses(status_id),
    current_location_id         INTEGER REFERENCES storage_locations(location_id),
    responsible_person_id       INTEGER REFERENCES users(user_id),
    remarks                     TEXT,
    created_at                  TEXT    DEFAULT (datetime('now')),
    updated_at                  TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_molds_mold_code ON molds(mold_code);

-- ── 借用状态字典 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loan_statuses (
    status_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT    NOT NULL UNIQUE,
    description TEXT
);

-- ── 模具借用记录 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_loan_records (
    loan_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id              INTEGER NOT NULL REFERENCES molds(mold_id),
    applicant_id         INTEGER NOT NULL REFERENCES users(user_id),
    loan_status_id       INTEGER REFERENCES loan_statuses(status_id),
    application_date     TEXT    DEFAULT (datetime('now')),
    expected_return_date TEXT,
    actual_return_date   TEXT,
    purpose              TEXT,
    remarks              TEXT,
    created_at           TEXT    DEFAULT (datetime('now')),
    updated_at           TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_mold_loan_records_mold_id ON mold_loan_records(mold_id);

-- ── 维修类型字典 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS maintenance_types (
    type_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name   TEXT    NOT NULL UNIQUE,
    is_repair   INTEGER DEFAULT 0,
    description TEXT
);

-- ── 维修结果状态字典 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS maintenance_result_statuses (
    status_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT    NOT NULL UNIQUE,
    description TEXT
);

-- ── 模具维修保养记录 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_maintenance_logs (
    log_id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id                      INTEGER NOT NULL REFERENCES molds(mold_id),
    maintenance_type_id          INTEGER REFERENCES maintenance_types(type_id),
    technician_id                INTEGER REFERENCES users(user_id),
    result_status_id             INTEGER REFERENCES maintenance_result_statuses(status_id),
    maintenance_start_timestamp  TEXT,
    maintenance_end_timestamp    TEXT,
    description                  TEXT,
    cost                         REAL,
    strokes_at_maintenance       INTEGER,
    created_at                   TEXT    DEFAULT (datetime('now')),
    updated_at                   TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_mold_maintenance_logs_mold_id ON mold_maintenance_logs(mold_id);

-- ── 模具部件分类字典 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_part_categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT    NOT NULL UNIQUE,
    description   TEXT
);

-- ── 模具部件 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_parts (
    part_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id           INTEGER NOT NULL REFERENCES molds(mold_id) ON DELETE CASCADE,
    part_code         TEXT    UNIQUE,
    part_name         TEXT    NOT NULL,
    part_category_id  INTEGER NOT NULL REFERENCES mold_part_categories(category_id),
    material          TEXT,
    supplier          TEXT,
    installation_date TEXT,
    lifespan_strokes  INTEGER,
    current_status_id INTEGER REFERENCES mold_statuses(status_id),
    remarks           TEXT,
    created_at        TEXT    DEFAULT (datetime('now')),
    updated_at        TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_mold_parts_mold_id ON mold_parts(mold_id);

-- ── 系统操作审计日志 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(user_id),
    action_type     TEXT    NOT NULL,
    target_resource TEXT,
    target_id       TEXT,
    details         TEXT,
    timestamp       TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_system_logs_user_id   ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_system_logs_timestamp ON system_logs(timestamp);

-- ── 登录失败计数 / 账号锁定（服务端，防止清会话绕过）────────────────
CREATE TABLE IF NOT EXISTS login_attempts (
    username     TEXT    PRIMARY KEY,
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_attempt TEXT,
    locked_until TEXT
);

-- ── 登录会话（服务端令牌，支持刷新页面后恢复登录态）──────────────────
CREATE TABLE IF NOT EXISTS user_sessions (
    session_token TEXT    PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    created_at    TEXT    DEFAULT (datetime('now')),
    expires_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user ON user_sessions(user_id);

-- ── 模次累计流水（molds.accumulated_strokes 的唯一审计来源）──────────
-- source_type: loan_return（借用归还）/ schedule_complete（排程完工）/ manual_adjust（台账手动调整）
CREATE TABLE IF NOT EXISTS mold_stroke_logs (
    stroke_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id       INTEGER NOT NULL REFERENCES molds(mold_id),
    strokes_added INTEGER NOT NULL,
    source_type   TEXT    NOT NULL,
    source_id     TEXT,
    operator_id   INTEGER REFERENCES users(user_id),
    remarks       TEXT,
    created_at    TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_stroke_logs_mold ON mold_stroke_logs(mold_id);

-- ── 生产设备 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS production_equipment (
    equipment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_code TEXT    NOT NULL UNIQUE,
    equipment_name TEXT    NOT NULL,
    equipment_type TEXT,
    tonnage        INTEGER,
    is_active      INTEGER DEFAULT 1,
    created_at     TEXT    DEFAULT (datetime('now'))
);

-- ── 产品表 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT    NOT NULL UNIQUE,
    product_name TEXT    NOT NULL,
    description  TEXT,
    created_at   TEXT    DEFAULT (datetime('now'))
);

-- ── 生产订单 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS production_orders (
    order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code   TEXT    NOT NULL UNIQUE,
    product_id   INTEGER REFERENCES products(product_id),
    quantity     INTEGER NOT NULL,
    due_date     TEXT,
    priority     INTEGER DEFAULT 5,
    status       TEXT    DEFAULT '待生产',
    created_at   TEXT    DEFAULT (datetime('now')),
    updated_at   TEXT    DEFAULT (datetime('now'))
);

-- ── 生产排程 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS production_schedules (
    schedule_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id       INTEGER REFERENCES production_orders(order_id),
    mold_id        INTEGER REFERENCES molds(mold_id),
    equipment_id   INTEGER REFERENCES production_equipment(equipment_id),
    scheduled_date TEXT,
    start_time     TEXT,
    end_time       TEXT,
    status         TEXT    DEFAULT '待执行',
    remarks        TEXT,
    created_at     TEXT    DEFAULT (datetime('now')),
    updated_at     TEXT    DEFAULT (datetime('now'))
);

-- ── 成本记录 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_records (
    record_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id      INTEGER REFERENCES molds(mold_id),
    cost_type    TEXT    NOT NULL,
    amount       REAL    NOT NULL,
    record_date  TEXT    DEFAULT (date('now')),
    description  TEXT,
    created_by   INTEGER REFERENCES users(user_id),
    created_at   TEXT    DEFAULT (datetime('now'))
);

-- ── 模具推荐 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mold_recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mold_id           INTEGER REFERENCES molds(mold_id),
    product_id        INTEGER REFERENCES products(product_id),
    score             REAL    DEFAULT 0,
    reason            TEXT,
    created_at        TEXT    DEFAULT (datetime('now'))
);

-- ════════════════════════════════════════════════════════════════════
-- 基础种子数据（幂等 upsert）
-- ════════════════════════════════════════════════════════════════════

-- 角色
INSERT INTO roles (role_name, description) VALUES
    ('超级管理员',  '系统最高权限，可管理所有数据'),
    ('模具库管理员','负责模具库日常管理'),
    ('模具工',      '负责模具维修保养'),
    ('冲压操作工',  '负责生产操作，可申请借用')
ON CONFLICT(role_name) DO UPDATE SET description = excluded.description;

-- 模具状态
INSERT INTO mold_statuses (status_name, description) VALUES
    ('闲置',       '模具可用状态'),
    ('使用中',     '模具正在使用'),
    ('已借出',     '模具已被借出'),
    ('已预定',     '模具已预定待借出'),
    ('外借申请中', '模具正在处理借用申请'),
    ('维修中',     '模具正在维修'),
    ('保养中',     '模具正在保养'),
    ('待维修',     '模具需要维修'),
    ('待保养',     '模具需要保养'),
    ('报废',       '模具已报废')
ON CONFLICT(status_name) DO UPDATE SET description = excluded.description;

-- 借用状态
INSERT INTO loan_statuses (status_name, description) VALUES
    ('待审批',     '申请已提交，等待审批'),
    ('已批准',     '申请已批准，等待处理'),
    ('已批准待借出','申请已批准，等待借出'),
    ('已借出',     '模具已借出使用'),
    ('已归还',     '模具已归还'),
    ('已驳回',     '申请被驳回'),
    ('逾期',       '超过预期归还时间'),
    ('外借申请中', '申请处理中，模具预留状态')
ON CONFLICT(status_name) DO UPDATE SET description = excluded.description;

-- 维修结果状态
INSERT INTO maintenance_result_statuses (status_name, description) VALUES
    ('待开始', '任务已创建，等待开始执行'),
    ('进行中', '维修保养工作正在进行'),
    ('完成待检','维修保养完成，等待质量检验'),
    ('合格可用','检验合格，可以正常使用'),
    ('失败待查','维修失败，需要进一步分析'),
    ('等待备件','等待备件到货后继续'),
    ('需要外协','需要外部专业机构协助')
ON CONFLICT(status_name) DO UPDATE SET description = excluded.description;

-- 维修类型
INSERT INTO maintenance_types (type_name, is_repair, description) VALUES
    ('定期保养', 0, '按计划周期保养'),
    ('故障维修', 1, '故障后紧急维修'),
    ('预防性维修',1, '预防性检查与修复'),
    ('大修',     1, '全面拆解检修')
ON CONFLICT(type_name) DO UPDATE SET description = excluded.description;

-- 模具功能类型
INSERT INTO mold_functional_types (type_name, description) VALUES
    ('冲裁模',   '用于冲孔、落料等冲裁工序'),
    ('弯曲模',   '用于板料弯曲成形'),
    ('拉深模',   '用于拉深成形'),
    ('成形模',   '用于各种复杂成形'),
    ('复合模',   '多工序复合模具'),
    ('级进模',   '多工位连续冲压模')
ON CONFLICT(type_name) DO UPDATE SET description = excluded.description;

-- 存放位置
INSERT INTO storage_locations (location_name, description) VALUES
    ('A库1号架', '主模具库A区1号架'),
    ('A库2号架', '主模具库A区2号架'),
    ('B库1号架', '备用模具库B区1号架'),
    ('B库2号架', '备用模具库B区2号架'),
    ('生产线1',  '1号生产线在用'),
    ('生产线2',  '2号生产线在用'),
    ('维修间',   '维修保养区')
ON CONFLICT(location_name) DO UPDATE SET description = excluded.description;

-- 模具部件分类
INSERT INTO mold_part_categories (category_name, description) VALUES
    ('凸模',   '冲头类零件'),
    ('凹模',   '凹模类零件'),
    ('导柱导套','导向零件'),
    ('弹簧',   '弹性元件'),
    ('螺钉销钉','紧固件'),
    ('其他',   '其他零件')
ON CONFLICT(category_name) DO UPDATE SET description = excluded.description;

-- 默认超级管理员账号（密码: Admin@123，首次登录请修改）
-- bcrypt hash of "Admin@123"
INSERT INTO users (username, password_hash, full_name, role_id, is_active)
SELECT 'admin',
       '$2b$12$nWBB6oeOhM1GL3tuUbWdM.H8t2KaZtFN7jgarxdI0MtPaLhmBkARa',
       '系统管理员',
       (SELECT role_id FROM roles WHERE role_name = '超级管理员'),
       1
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');
