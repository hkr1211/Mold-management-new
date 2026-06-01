# 蕴杰模具全生命周期管理系统 — 项目索引

> 版本：v1.4.0｜索引更新时间：2026-04-30｜维护人：jerry.houyong@gmail.com

---

## 1. 项目概览

**系统定位**：面向冲压制造企业的模具台账与流程管理 Web 应用（Streamlit 多页面）。  
**核心能力**：模具管理、借用管理、维修/保养、部件管理、模具推荐、成本分析、生产排程、系统管理（用户/日志）。  

**当前默认部署**：Docker Compose（Streamlit App + SQLite 文件库 + Nginx 反向代理 + 定时备份容器）。  

> 注意：项目历史上曾使用 PostgreSQL + Alembic（相关配置仍保留在 `alembic/`、`alembic.ini`、部分 SQL 脚本中），但当前运行路径以 SQLite 为主（见 `app/utils/database.py` 与 `sql/sqlite_init.sql`）。

---

## 2. 技术栈（以当前代码为准）

| 层次 | 技术/实现 |
|---|---|
| UI / 前端 | Streamlit（多页面：`app/pages/*.py`） |
| 业务逻辑 | Python 3.11（Streamlit `session_state` 驱动） |
| 数据库 | SQLite（默认文件：`data/mold_management.db`，可用 `SQLITE_DB_PATH` 覆盖） |
| DB 访问 | `sqlite3` + 统一封装 `execute_query()`（对 `%s/ILIKE/NOW()` 等做了 SQL 方言归一） |
| Schema/文档 | SQL 初始化脚本：`sql/sqlite_init.sql`；SQLAlchemy 模型：`app/utils/models.py`（主要用于“schema 文档/迁移辅助”，非运行时依赖） |
| 认证与权限 | `bcrypt` 哈希 + 登录失败锁定 + `ROLE_PERMISSIONS` 权限字典 + `require_permission` 装饰器 |
| 数据分析/可视化 | pandas / numpy（页面中使用） |
| 容器化与网关 | Docker / docker-compose；Nginx（反向代理、WebSocket、静态资源缓存、安全响应头） |
| 自动备份 | `scripts/backup.sh`（备份 SQLite 文件，保留 7 天） |
| 测试 | `pytest`（`tests/test_auth.py`, `tests/test_database.py`，偏单元/隔离测试） |

---

## 3. 目录结构（Top-level）

```
.
├── app/
│   ├── main.py                 # 入口：首页/登录/仪表盘
│   ├── pages/                  # Streamlit 多页面（业务模块）
│   ├── utils/                  # auth/database/models 等通用模块
│   └── config/                 # 全局配置（settings.py 有效；database.py 当前为空）
├── data/
│   └── mold_management.db       # SQLite 数据库文件（可用 volume 持久化）
├── sql/
│   ├── sqlite_init.sql          # SQLite：建表 + 字典/种子数据（幂等）
│   └── complete_init.sql        # 历史/混合脚本（含 PostgreSQL 风格语法，需谨慎使用）
├── alembic/                     # 历史迁移体系（当前 env.py 默认拼接 PostgreSQL URL）
├── nginx/
│   └── nginx.conf               # HTTPS 反代、WebSocket、缓存、安全头
├── scripts/
│   ├── gen_cert.sh              # 生成自签证书（配合 Nginx HTTPS）
│   └── backup.sh                # 备份 SQLite（由 backup 容器定时运行）
├── tests/
│   ├── test_auth.py
│   └── test_database.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 4. 主要模块与入口

### 4.1 Streamlit 页面（业务模块）

- `1_模具管理.py`：模具台账、查询、创建、编辑
- `2_借用管理.py`：借用申请/审批/借出/归还流程（依赖 `loan_statuses` 与模具状态联动）
- `3_维修管理.py`：维修保养任务、状态流转
- `4_部件管理.py`：模具部件与“压边圈”专项管理（依赖 `mold_part_categories`、`mold_parts`）
- `5_系统管理.py`：系统参数、用户管理、审计日志
- `6_模具推荐.py`：推荐算法与推荐结果落库（`mold_recommendations`）
- `7_成本分析.py`：成本统计（`cost_records`）
- `8_生产排程.py`：生产订单/排程（`production_orders` / `production_schedules` / `production_equipment`）

### 4.2 通用能力

- `app/utils/database.py`：SQLite 连接、SQL 方言归一、白名单标识符校验、CRUD 查询封装、初始化导入（模块导入时会执行 `initialize_database()`）
- `app/utils/auth.py`：登录、密码策略、权限判定与页面级装饰器 `require_permission`
- `app/config/settings.py`：全局配置（DB_PATH、缓存 TTL、密码与锁定策略等）

---

## 5. 数据库（SQLite）概览

**Schema 来源**：`sql/sqlite_init.sql`（幂等脚本，包含建表与字典/种子数据）。  
**默认管理员**：`admin / Admin@123`（首次登录建议修改）。  

核心业务表：
- `molds`（模具主数据）
- `mold_loan_records`（借用记录）
- `mold_maintenance_logs`（维修保养记录）
- `mold_parts`（部件）
- `system_logs`（审计日志）
- `production_*`（排程相关）
- `cost_records`（成本）
- `mold_recommendations`（推荐记录）

---

## 6. 部署与运行（当前 docker-compose）

### 6.1 启动

```bash
docker-compose up -d --build
```

### 6.2 访问

- 通过 Nginx：默认 **80 强制跳转 443**，因此优先访问 `https://localhost`
- 直连 Streamlit：`http://localhost:8501`

> 若未准备证书，需先在 `nginx/ssl/` 放置 `server.crt/server.key`（仓库提供了 `scripts/gen_cert.sh` 作为自签证书生成脚本）。

---

## 7. 已知问题与技术债务（基于现状梳理）

1. **缺少 `requirements.txt`**：但 `Dockerfile` 使用 `COPY requirements.txt`，会导致镜像构建失败。
2. **SQLite 与 Alembic/PostgreSQL 配置不一致**：`alembic/env.py` 默认拼接 PostgreSQL URL；`alembic.ini` 也偏 PostgreSQL，容易误导。
3. **`app/config/database.py` 与 `app/__init__.py` 为空文件**：存在“结构占位/历史残留”迹象。
4. **模块导入即初始化 DB**：`app/utils/database.py` 末尾自动执行 `initialize_database()`，可导致测试/脚本导入时产生副作用（虽测试做了 patch，但仍建议架构化）。
5. **SQL 脚本混用方言**：`sql/complete_init.sql` 含 PostgreSQL 风格 `SERIAL/TIMESTAMPTZ/EXCLUDED` 等语法，与 SQLite 不兼容。
