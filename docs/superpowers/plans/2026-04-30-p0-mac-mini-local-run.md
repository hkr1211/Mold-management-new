# P0（Mac mini 本地跑通 / SQLite / 直连 8501）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复当前仓库的 P0 阻塞项，使其在 Mac mini 上执行 `docker compose up -d --build` 即可成功启动（默认直连 8501），不被 Nginx HTTPS/证书问题阻塞。

**Architecture:** 保持 SQLite 运行路径不变；只做最小工程化改造：补齐 Python 依赖清单 + 将 nginx/backup 设为可选 profile，从而默认只启动 app 服务。

**Tech Stack:** Docker Compose, Python 3.11, Streamlit, SQLite

---

## 变更文件一览

**Create:**
- `requirements.txt`

**Modify:**
- `docker-compose.yml`

**Verify (commands):**
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl -I http://localhost:8501`

---

### Task 1: 新增 requirements.txt（解决 Docker 构建阻塞）

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: 创建 requirements.txt（最小可运行依赖集）**

内容（直接写入文件）：
```txt
# Web UI
streamlit>=1.32,<2

# Data
pandas>=2.0,<3
numpy>=1.24,<3

# Charts
plotly>=5.18,<6

# Auth
bcrypt>=4,<5

# System / Ops
psutil>=5.9,<6

# Schema docs / migrations (历史遗留仍会 import)
SQLAlchemy>=2,<3
alembic>=1.12,<2

# Tests
pytest>=8,<9
```

- [ ] **Step 2: 本地构建镜像验证 requirements.txt 可用**

Run:
```bash
docker compose build
```

Expected:
- `app` 镜像构建成功（退出码 0）
- pip 安装依赖过程中无 “No matching distribution found” / “ResolutionImpossible”

---

### Task 2: 将 nginx/backup 改为可选 profile（避免默认被 HTTPS/证书阻塞）

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 为 nginx/backup 增加 profiles，并保持 app 为默认启动**

将 `docker-compose.yml` 中的服务调整为：
1) `app` 不加 profiles（默认启动）
2) `nginx` 增加 `profiles: ["edge"]`
3) `backup` 增加 `profiles: ["backup"]`

示例目标结构（仅示意 profiles 字段；其余配置保持原样）：
```yaml
services:
  app:
    ...

  nginx:
    profiles: ["edge"]
    ...

  backup:
    profiles: ["backup"]
    ...
```

- [ ] **Step 2: 校验 compose 配置**

Run:
```bash
docker compose config
```

Expected:
- 输出的最终配置中，`nginx`/`backup` 均包含 `profiles` 字段

- [ ] **Step 3: 默认一键启动只起 app（P0 验收）**

Run:
```bash
docker compose up -d --build
docker compose ps
```

Expected:
- `app` 为 running
- `nginx`、`backup` 不会启动（除非显式指定 profile）

- [ ] **Step 4: 验证 8501 可访问**

Run:
```bash
curl -I http://localhost:8501
```

Expected:
- HTTP 响应码为 `200` 或 `302`（Streamlit 常见会有重定向），且连接成功

- [ ] **Step 5:（可选）验证 profile 可按需启用**

启用备份：
```bash
docker compose --profile backup up -d
docker compose ps
```

启用 Nginx（若你已经准备好证书并愿意处理 https）：
```bash
docker compose --profile edge up -d
docker compose ps
```

---

## 自检清单（Plan Self-Review）

- [ ] plan 覆盖了 P0 阻塞项：缺失 `requirements.txt`、默认启动被 Nginx/证书干扰
- [ ] plan 中无 TBD/TODO/“自行处理”式空步骤
- [ ] 所有文件路径、命令、期望结果明确

