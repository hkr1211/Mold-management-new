# P1（本地运行说明与可选服务启用）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已完成 P0（可 build/可默认直连 8501）的基础上，补齐“如何在 Mac mini 局域网运行”的文档与环境示例，降低部署摩擦。

**Architecture:** 仅新增/修改文档文件，不改业务代码；明确：默认直连 8501，nginx/backup 通过 compose profiles 可选启用。

**Tech Stack:** Docker Compose, Streamlit, SQLite

---

## 变更文件一览

**Create:**
- `.env.example`
- `RUNBOOK.md`

**Modify:**
- `README.md`

---

### Task 1: 新增 .env.example（环境变量示例）

**Files:**
- Create: `.env.example`

- [ ] **Step 1: 写入示例内容**

```env
# SQLite 数据库路径（容器内路径）
SQLITE_DB_PATH=/app/data/mold_management.db

# 如需启用 Nginx/备份，请使用 compose profiles（见 RUNBOOK.md）
```

---

### Task 2: 新增 RUNBOOK.md（Mac mini 局域网运行手册）

**Files:**
- Create: `RUNBOOK.md`

- [ ] **Step 1: 写入 RUNBOOK 关键章节**

必须包含：
1) 一键启动命令（默认直连 8501）
2) 如何获取 Mac mini 局域网 IP（用 `ipconfig getifaddr en0` / `ifconfig` 说明）
3) 局域网访问方式：`http://<mac-ip>:8501`
4) 如何启用可选服务
   - `docker compose --profile backup up -d`
   - `docker compose --profile edge up -d`（并注明证书/HTTPS 跳转注意事项）
5) 常见问题（端口占用、容器重启、数据持久化、备份恢复）

---

### Task 3: 更新 README.md（纠正技术栈描述 + 指向 RUNBOOK）

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 将 README 从“PostgreSQL/拼写错误描述”更新为“SQLite + Streamlit + Docker”**
- [ ] **Step 2: 增加快速开始（Quick Start）与 RUNBOOK 链接**

---

### Task 4: 验证（文档一致性）

- [ ] **Step 1: 确认 README/RUNBOOK 中的命令与 compose profiles 一致**
- [ ] **Step 2: 提交 git（仅文档类文件）**

Commit message 建议：
```bash
git add README.md RUNBOOK.md .env.example
git commit -m "docs: add mac mini runbook and env example"
```

