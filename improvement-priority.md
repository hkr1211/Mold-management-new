# 改进优先级清单（汇总自评估）

> 规则：以 **影响（Impact）× 风险（Risk）÷ 成本（Cost）** 做粗排序。  
> 标记：P0=阻塞/高风险；P1=重要；P2=优化；P3=可延后。

---

## P0（必须先做：阻塞交付/高风险）

1) **补齐依赖文件并修复 Docker 构建链路**
   - 症状：`Dockerfile` 依赖 `requirements.txt`，仓库中缺失，`docker-compose up --build` 将失败。
   - 建议：
     - 方案 A：补 `requirements.txt`（锁版本）；或
     - 方案 B：引入 `pyproject.toml` + `uv/pip-tools/poetry`，并同步修改 Dockerfile。

2) **明确数据库路线：SQLite vs PostgreSQL/Alembic**
   - 症状：运行时使用 SQLite；但 `alembic/env.py` 仍拼接 PostgreSQL URL，`complete_init.sql` 也偏 PostgreSQL。
   - 建议：
     - 若确定 SQLite：标记/移除 Alembic 相关路径或改造成 SQLite 可用的迁移方式；
     - 若要回归 PostgreSQL：同步恢复 docker-compose/db 服务、重建 `utils/database.py` 连接层与初始化脚本。

3) **HTTPS 默认强制跳转的“首次启动体验”治理**
   - 症状：Nginx 80 → 443 强制跳转，若未准备证书会导致访问失败。
   - 建议：提供一键生成证书/关闭跳转的运行开关（例如环境变量控制），并补充 README 指引。

---

## P1（重要：降低长期维护成本/降低事故概率）

4) **将“导入即初始化 DB”的副作用改为显式启动流程**
   - 现状：`utils/database.py` 文件末尾执行 `initialize_database()`。
   - 风险：任何 import 都可能写磁盘/建表；测试与脚本需要打补丁绕过。
   - 建议：改为在 `app/main.py` 启动时调用；或提供 `init_db()` 显式入口并按环境开关。

5) **抽取业务层与数据访问层，降低页面脚本复杂度**
   - 现状：页面文件聚合 UI + SQL + 状态流转，难以复用与测试。
   - 建议：逐步提取：
     - `services/`：业务规则（借用/维修/排程/推荐/成本）
     - `repos/`：DB 查询（按实体/聚合）
     - `ui/components/`：可复用 UI 片段（过滤器、表格、详情卡片等）

6) **完善配置与环境管理**
   - 增补：`.env.example`、运行参数说明、日志级别与调试开关、数据目录/备份目录说明。

---

## P2（优化：体验/性能/可观测性）

7) **查询分页与大数据量优化**
   - 对列表页统一分页/limit/offset；
   - 对常用过滤字段补索引（SQLite 现有部分索引已建立，但可覆盖更多查询路径）。

8) **权限体系与审计日志标准化**
   - 将 action_type 统一枚举化；
   - 日志 details 结构化（JSON schema）；
   - 关键操作补充目标 ID 与变更摘要。

9) **观测能力**
   - 增加基础健康检查页面/指标；
   - 统一日志格式（时间、用户、模块、请求/页面）。

---

## P3（可延后：清理与一致性）

10) **清理历史/空文件与文档一致性**
   - `app/config/database.py` 空文件：删除或实现
   - `sql/complete_init.sql` 的方言标注与用途说明（避免误用）
   - README 扩写：安装、启动、证书、备份与恢复

11) **迁移体系一致性**
   - 若保留 SQLAlchemy models：明确其与 SQLite schema 的同步策略（自动生成/手工维护/弃用）。

