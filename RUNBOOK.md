# Mac mini 局域网运行手册（Docker Compose）

本文说明如何在 Mac mini 上用 Docker Compose 启动本项目，并让同一局域网内的其他设备访问。

## 0. 前置条件

- 已安装并启动 Docker（Docker Desktop / Colima 均可）
- Mac mini 与访问端设备在同一局域网（同一路由器/同一网段）

## 1. 默认启动（直连 Streamlit 8501）

在项目根目录执行：

```bash
docker compose up -d --build
```

启动后：

- Mac mini 本机访问：`http://localhost:8501`
- 局域网其他设备访问：`http://<Mac-mini-局域网IP>:8501`

### 获取 Mac mini 局域网 IP

常用方式（任选其一）：

```bash
# Wi‑Fi 通常是 en0
ipconfig getifaddr en0

# 或查看所有网卡地址
ifconfig | grep "inet " | grep -v 127.0.0.1
```

提示：若其他设备无法访问，请检查 macOS 防火墙/安全软件是否阻止了 8501 端口。

## 2. 可选：启用 backup profile（每日自动备份 SQLite）

`backup` 服务默认不启动，需要显式启用 profile：

```bash
docker compose --profile backup up -d --build
```

说明：

- 备份从 `sqlite_data` 卷读取数据库文件并写入 `db_backups` 卷
- 默认每天 02:00 进行备份（容器内 cron）

## 3. 可选：启用 edge（nginx）profile（80/443 入口）

`edge` profile 会启动 `nginx`，并且 **默认 80 → 443 强制跳转**（见 `nginx/nginx.conf`）。

### 3.1 证书准备（必须）

`edge` 需要证书文件：

- `nginx/ssl/server.crt`
- `nginx/ssl/server.key`

开发/内网可使用脚本生成自签名证书（建议把局域网 IP 作为参数）：

```bash
sh scripts/gen_cert.sh <Mac-mini-局域网IP>
```

浏览器首次访问会提示证书不受信任，可在“高级”中选择继续访问。

### 3.2 启动 edge（nginx）

```bash
docker compose --profile edge up -d --build
```

访问方式：

- `http://<IP>/` 会跳转到 `https://<IP>/`
- 直接访问：`https://<IP>/`

## 4. 同时启用 backup + edge

```bash
docker compose --profile backup --profile edge up -d --build
```

## 5. 常用运维命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f --tail=200 app

# 停止（保留卷数据）
docker compose down

# 停止并删除卷（会清空 SQLite 数据与备份，不建议）
docker compose down -v
```

