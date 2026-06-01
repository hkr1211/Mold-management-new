# /memory — 项目技术栈与业务规则（落地版）

> 说明：你要求“写入 /memory”。在当前工作区中，我用本文件作为可版本化的“项目记忆（Memory）”。后续如需拆分成多份（例如 `/memory/tech-stack.md`、`/memory/business-rules.md`），可继续演进。

---

## 1) 技术栈（运行时事实）

### 应用与运行
- **框架**：Streamlit（多页面：`app/pages/*.py`）
- **语言**：Python 3.11
- **入口**：`app/main.py`
- **会话**：Streamlit `st.session_state`（登录态与角色信息存储于会话中）

### 数据库
- **数据库**：SQLite（文件库）
- **默认 DB 文件**：`data/mold_management.db`
- **环境变量**：`SQLITE_DB_PATH` 可覆盖 DB 文件路径
- **连接/封装**：`app/utils/database.py`
  - 每线程独立连接（thread-local）
  - `WAL` 模式 + `foreign_keys=ON`
  - SQL 方言归一：`%s → ?`、`NOW() → datetime('now')`、`ILIKE → LIKE` 等

### 认证与权限
- **密码**：bcrypt
- **密码强度规则**（`validate_password_strength`）：
  - 长度 ≥ `PASSWORD_MIN_LENGTH`（默认 8）
  - 必须包含：大写字母/小写字母/数字
- **登录风控**：
  - 最大失败次数：`LOGIN_MAX_ATTEMPTS`（默认 5）
  - 锁定时长：`LOGIN_LOCKOUT_SECONDS`（默认 300 秒）
- **权限模型**：
  - `ROLE_PERMISSIONS` 字典（按角色定义权限集合）
  - `has_permission(permission)`
  - 页面级保护：`@require_permission(permission)`

### 部署与网关
- **Dockerfile**：容器中启动 `streamlit run app/main.py`
- **docker-compose**：
  - `app`：Streamlit
  - `nginx`：反向代理（含 WebSocket）
  - `backup`：定时备份 SQLite 文件
- **Nginx 关键点**：
  - 80 端口强制跳转 443（HTTPS）
  - 安全响应头（X-Frame-Options 等）

---

## 2) 核心业务对象（数据模型）

以下以 `sql/sqlite_init.sql` 的建表为准：

### 用户与角色
- `roles(role_id, role_name, description)`
- `users(user_id, username, password_hash, full_name, email, role_id, is_active, created_at, updated_at)`

### 模具主数据
- `molds(mold_id, mold_code[唯一], mold_name, ... , current_status_id, current_location_id, responsible_person_id, ...)`

### 借用
- `loan_statuses(status_id, status_name, description)`
- `mold_loan_records(loan_id, mold_id, applicant_id, loan_status_id, application_date, expected_return_date, actual_return_date, ...)`

### 维修/保养
- `maintenance_types(type_id, type_name, is_repair, description)`
- `maintenance_result_statuses(status_id, status_name, description)`
- `mold_maintenance_logs(log_id, mold_id, maintenance_type_id, technician_id, result_status_id, ... )`

### 部件
- `mold_part_categories(category_id, category_name, description)`
- `mold_parts(part_id, mold_id, part_code[唯一/可空], part_name, part_category_id, ... )`

### 审计日志
- `system_logs(log_id, user_id, action_type, target_resource, target_id, details, timestamp)`

### 生产与成本
- `production_equipment(...)`
- `products(...)`
- `production_orders(...)`
- `production_schedules(...)`
- `cost_records(...)`
- `mold_recommendations(...)`

---

## 3) 字典/枚举（系统内置规则）

### 3.1 角色（seed）
- 超级管理员
- 模具库管理员
- 模具工
- 冲压操作工

### 3.2 模具状态（`mold_statuses` seed）
闲置、使用中、已借出、已预定、外借申请中、维修中、保养中、待维修、待保养、报废

### 3.3 借用状态（`loan_statuses` seed）
待审批、已批准、已批准待借出、已借出、已归还、已驳回、逾期、外借申请中

### 3.4 维修结果状态（`maintenance_result_statuses` seed）
待开始、进行中、完成待检、合格可用、失败待查、等待备件、需要外协

### 3.5 维修类型（`maintenance_types` seed）
定期保养（is_repair=0）、故障维修（1）、预防性维修（1）、大修（1）

---

## 4) 权限规则（ROLE_PERMISSIONS）

以 `app/utils/auth.py` 为准（粗粒度权限）：

- 超级管理员：`*`（所有权限）
- 模具库管理员：
  - `view_molds`, `manage_molds`, `approve_loans`, `view_reports`, `manage_schedule`, `manage_users`
- 模具工：
  - `view_molds`, `manage_maintenance`, `view_own_tasks`
- 冲压操作工：
  - `view_molds`, `create_loan`, `view_own_loans`, `view_schedule`

---

## 5) 关键业务流程（业务规则摘要）

### 5.1 登录
1) 输入用户名/密码  
2) 校验 `users` + bcrypt 哈希  
3) 登录成功写入 `session_state`：`logged_in/user_id/username/full_name/user_role`  
4) 写入审计日志 `system_logs`（action_type: `LOGIN` / `LOGOUT`）

### 5.2 模具管理（概要）
- 模具编号 `mold_code` 全局唯一
- 主要状态、位置、负责人均为外键引用字典/用户表
- 页面层有权限控制（至少 `view_molds`；新增/编辑需要 `manage_molds`）

### 5.3 借用管理（概要）
- 借用记录写入 `mold_loan_records`，并跟随 `loan_statuses` 状态流转
- 典型状态：待审批 → 已批准/已驳回 → 已批准待借出 → 已借出 → 已归还
- 业务上通常需要联动更新模具 `molds.current_status_id`（例如闲置/外借申请中/已借出/闲置）

### 5.4 维修/保养（概要）
- 任务写入 `mold_maintenance_logs`
- 结果状态按 `maintenance_result_statuses` 流转
- 可基于 `molds.accumulated_strokes` 与 `maintenance_cycle_strokes` 进行“到期提醒/触发”（具体规则以页面实现为准）

### 5.5 部件（含压边圈专项）
- `mold_parts` 绑定 `molds`
- “压边圈”是通过 `mold_part_categories` 中的类别名称模糊匹配实现的专项视图（category_name LIKE '%压边圈%'）

---

## 6) 默认账号（seed）

来自 `sql/sqlite_init.sql`：
- `admin / Admin@123`（bcrypt hash 已写入，提示“首次登录请修改”）

