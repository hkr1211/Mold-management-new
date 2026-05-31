# 项目评估记录（逐模块 × 分维度）

> 评估基于仓库现状（2026-04-30）静态审阅：目录结构、关键 Python 模块、SQL 初始化脚本、Docker/Nginx 配置与测试用例。  
> 评分采用 **1~5**：5=优秀/规范，3=可用但有明显提升空间，1=风险高/需要优先治理。

---

## 模块清单（用于各轮复用）

| 模块 | 说明 |
|---|---|
| `app/main.py` | Streamlit 入口、登录页、仪表盘 |
| `app/pages/*` | 8 个业务页面（模具/借用/维修/部件/系统/推荐/成本/排程） |
| `app/utils/database.py` | SQLite 连接与查询封装、初始化逻辑 |
| `app/utils/auth.py` | 登录、密码策略、权限体系、审计日志 |
| `app/utils/models.py` | SQLAlchemy ORM 模型（更偏“schema 文档/迁移辅助”） |
| `sql/sqlite_init.sql` | SQLite schema + seed 数据（幂等） |
| `docker-compose.yml` / `Dockerfile` | 容器化与启动 |
| `nginx/nginx.conf` | 反向代理、HTTPS/WebSocket、安全头 |
| `tests/*` | pytest 单元测试（隔离 mock） |
| `alembic/*` | 历史迁移（当前偏 PostgreSQL） |

---

## 第 1 轮：架构与模块边界（每模块）

| 模块 | 评分 | 主要发现 |
|---|---:|---|
| `app/main.py` | 4 | 入口组织清晰、UI 体验投入较多；但逻辑与 UI 同文件，后续可拆分服务层/组件层。 |
| `app/pages/*` | 3 | 按业务拆分为多页面是正确方向；但页面文件整体偏“巨型脚本”，缺少领域层抽象与复用。 |
| `utils/database.py` | 3 | 统一 DB 封装、方言归一与白名单校验是加分项；但“导入即初始化 DB”会带来副作用与测试成本。 |
| `utils/auth.py` | 4 | 认证/权限体系较完整（锁定、强度校验、装饰器）；仍是脚本式组织，可抽象服务/仓储层。 |
| `utils/models.py` | 2 | SQLAlchemy 模型与 SQLite schema 的关系不够明确；目前又与 Alembic/Postgres 绑定，容易产生“迁移体系漂移”。 |
| `sql/sqlite_init.sql` | 4 | 幂等建表 + 种子数据明确，是可落地的 schema 来源。 |
| Docker/Nginx | 2 | docker-compose 和 Nginx 思路正确；但 **Dockerfile 依赖 `requirements.txt` 缺失** 会导致构建失败；HTTPS 强制跳转也会增加首次启动门槛。 |
| `tests/*` | 4 | 用 mock 使模块可被隔离测试，且覆盖了权限与注入防护；仍缺集成测试与关键业务流测试。 |
| `alembic/*` | 1 | env.py 明确拼接 PostgreSQL URL，与当前 SQLite 路径冲突；如果继续保留需明确“弃用/迁移/双栈”策略。 |

---

## 第 2 轮：可维护性与工程化（每模块）

| 模块 | 评分 | 主要发现 |
|---|---:|---|
| `app/pages/*` | 2 | 页面多处存在：SQL 直写、重复 UI 片段、状态机分散、代码行数偏大；建议逐步提取 `services/`（业务）与 `repos/`（数据访问）以及共享组件。 |
| `utils/database.py` | 3 | 有类型转换/参数序列化/白名单校验；但职责稍多（连接、SQL 变换、安全、初始化、CRUD 都在一个文件）。 |
| `utils/auth.py` | 3 | 认证、权限、用户管理、密码策略集中在一个文件；可拆分 `auth_service` / `user_service` / `permission`。 |
| `config/settings.py` | 4 | 配置集中，且支持环境变量覆盖；推荐补齐 `.env.example` 与运行说明。 |
| `config/database.py` | 1 | 空文件：需要删除或实现（避免误导）。 |
| Docker | 1 | 缺 `requirements.txt`；缺少镜像构建可复现性（锁版本、依赖扫描）。 |

---

## 第 3 轮：安全（每模块）

| 模块 | 评分 | 主要发现 |
|---|---:|---|
| `utils/database.py` | 4 | SQL 参数化 + 标识符正则校验 + 表名白名单，对抗注入有效；错误日志未直接打印参数值（仅打印“参数数量”）是加分。 |
| `utils/auth.py` | 3 | bcrypt + 锁定策略 + 密码强度校验不错；但会话仅在 `session_state`，缺 CSRF/会话持久化与多端登录策略（Streamlit 的局限需接受或补充）。 |
| Nginx | 4 | 配置了安全响应头、WebSocket 代理；但默认强制 HTTPS 且依赖证书文件，部署时需明确证书管理与内网策略（HSTS 注释是谨慎的）。 |
| Docker/Secrets | 2 | 目前缺 `.env` 管理示例；若未来引入外部 DB/SMTP 等，需要规范化 secrets。 |

---

## 第 4 轮：性能与扩展性（每模块）

| 模块 | 评分 | 主要发现 |
|---|---:|---|
| SQLite 路径 | 3 | WAL + per-thread 连接对单机并发友好；但 Streamlit 多用户并发下仍可能遇到锁竞争，尤其在写入频繁场景。 |
| 页面查询 | 3 | 多处用 `@st.cache_data` 缓解读压力；但不少查询未分页/未限制结果集，数据量变大后风险上升。 |
| Nginx | 4 | 静态资源长缓存 + WebSocket 代理，配置合理。 |

---

## 第 5 轮：测试、发布与可观测性（每模块）

| 模块 | 评分 | 主要发现 |
|---|---:|---|
| 单元测试 | 4 | `auth` 与 `database` 有针对性测试；对安全白名单与密码策略有覆盖。 |
| 发布/构建 | 1 | Docker 构建链路断裂（缺 `requirements.txt`）；缺 CI（lint/test/build）。 |
| 日志 | 3 | Python logging 有使用；建议统一格式、增加 request/用户上下文、按环境控制级别。 |
| 备份 | 4 | SQLite 文件备份脚本清晰，并带保留策略；建议补充恢复演练/校验。 |

