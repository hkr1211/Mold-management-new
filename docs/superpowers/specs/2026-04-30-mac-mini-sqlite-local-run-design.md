# 设计说明：Mac mini（局域网）先跑通业务，再迁移 Windows Server（SQLite）

日期：2026-04-30  
范围：**最小可运行改造**（Make it run on Mac mini, LAN only, SQLite）  

---

## 1. 背景与目标

用户计划：
1) 先在本地 **Mac mini** 上跑通全部业务流程  
2) 再迁移到 **Windows Server**  

约束：
- 本应用为**局域网内部使用**，不需要互联网访问
- 选择 **SQLite** 作为数据库即可
- 期望 **一键启动**（优先 Docker），并能从局域网其它机器访问

目标（验收标准）：
- 在 Mac mini 上执行 `docker compose up -d --build` 可成功启动
- 局域网内任意电脑访问 `http://<MacMini_IP>:8501` 可打开登录页并完成核心业务流（登录/模具/借用/维修/部件/系统日志等）
- 重启容器后数据不丢（SQLite 数据持久化到 volume 或固定路径）

非目标：
- 互联网暴露、外网访问、SaaS 化
- 在第一阶段强制 HTTPS、证书自动签发
- 切换到 PostgreSQL（可作为后续选项，不在本次最小改造中）

---

## 2. 当前仓库关键事实（现状审计）

### 2.1 数据库现状
- 运行时代码使用 SQLite：`app/utils/database.py` + `sql/sqlite_init.sql`
- 默认数据库文件：`data/mold_management.db`
- 支持环境变量覆盖：`SQLITE_DB_PATH`
- 模块导入时会执行 `initialize_database()`（存在副作用，但本次先不改架构，只保证可跑通）

### 2.2 Docker / Nginx 现状
- `docker-compose.yml` 已暴露 `8501:8501`，可直连 Streamlit
- `nginx/nginx.conf` 配置为：**80 强制跳转 443**；依赖 `nginx/ssl/server.crt` 与 `server.key`
- `scripts/backup.sh` 提供 SQLite 文件每日备份逻辑（backup 容器 cron 执行）

### 2.3 阻塞点
- `Dockerfile` 执行 `COPY requirements.txt .` 并 `pip install -r requirements.txt`  
  **但仓库不存在 `requirements.txt`** → 导致构建失败 → 一键启动失败

---

## 3. 推荐方案与取舍

### 方案 A（推荐）：默认只启动 Streamlit（直连 8501），其它服务可选

做法：
- 让 `docker compose up -d --build` 默认仅启动 `app`（以及 SQLite 持久化 volume）
- `nginx` 与 `backup` 改为“可选启用”（例如 compose profiles 或拆分 compose 文件）

优点：
- 最少坑、最快跑通业务
- 不会被 HTTPS/证书问题卡住

缺点：
- 第一阶段没有统一入口（不经 Nginx）
- 没有 HTTPS（但局域网内部可接受）

### 方案 B：继续默认带 Nginx，但禁用 HTTPS 强跳（仅 HTTP 80）

优点：统一入口  
缺点：仍要处理 Nginx/证书策略的演进；比方案 A 多一个变量

结论：先用方案 A 跑通业务，后续再按需要启用 Nginx/HTTPS。

---

## 4. 设计变更清单（最小可运行）

### 4.1 必做（P0：保证“能 build & 能跑”）
1) 新增 `requirements.txt`
   - 内容：与当前代码实际 import 匹配（streamlit/pandas/numpy/plotly/bcrypt/pytest 等）
   - 策略：优先锁定主版本范围，避免“最新不兼容”

2) 调整 `docker-compose.yml` 默认启动行为
   - 默认启用 `app`
   - `nginx` 与 `backup` 改为可选（profiles：`edge`/`backup` 等）
   - 保留 `8501:8501`，方便局域网直连访问
   - 保留 `sqlite_data` volume（挂载到 `/app/data`）

### 4.2 应用运行说明（P1：减少运维摩擦）
3) 增加 `RUNBOOK.md`（或 README 扩写）
   - Mac mini 启动命令
   - 局域网访问地址获取方式（Mac IP）
   - 常见故障（端口占用、权限、证书、volume 数据）
   - 如何启用 `nginx` profile（如果需要统一入口）
   - 如何启用 `backup` profile（如果需要自动备份）

4) 增加 `.env.example`
   - `SQLITE_DB_PATH`（可选）
   - 可选启用项说明（以文档为准）

---

## 5. 迁移到 Windows Server 的策略（第二阶段，不在本次改造范围内）

保持 Docker 化迁移：
- 将项目目录复制到 Windows Server
- 同步迁移 SQLite 数据（优先迁移 volume 对应的数据，或直接迁移 `mold_management.db` 文件）
- 若启用 Nginx：在 Windows 上也按同样方式配置证书与端口映射

---

## 6. 风险与回滚

风险：
- 依赖版本选择不当导致运行报错（通过 `docker build` 验证）
- Windows 与 Mac 的文件权限/路径差异导致 volume 挂载不一致（通过“固定 volume + 明确路径”降低）

回滚：
- 所有变更均为新增文件 + compose 行为调整，可通过回退 commit 或切换 compose 文件恢复

