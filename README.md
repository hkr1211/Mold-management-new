# Mold Management（SQLite + Streamlit + Docker）

蕴杰模具全生命周期管理系统：使用 **Streamlit** 构建界面，默认使用 **SQLite** 作为数据存储，并提供 **Docker Compose** 一键启动（可选 Nginx 作为 edge 入口、可选每日备份）。

## Quick Start

在项目根目录执行：

```bash
docker compose up -d --build
```

然后在浏览器打开：

- 本机：`http://localhost:8501`
- 局域网：`http://<Mac-mini-局域网IP>:8501`

更多 Mac mini 局域网运行说明（含获取 IP、可选启用 backup/edge profiles 等）请见：

- [RUNBOOK.md](./RUNBOOK.md)

## 配置

应用支持通过环境变量覆盖 SQLite 文件路径：

- `SQLITE_DB_PATH`（示例见 [.env.example](./.env.example)）
