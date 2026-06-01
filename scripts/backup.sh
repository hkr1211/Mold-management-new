#!/bin/sh
# scripts/backup.sh — SQLite 每日自动备份（在 backup 容器内运行）

set -e

DB_FILE="/data/mold_management.db"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/mold_db_${TIMESTAMP}.db"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_FILE" ]; then
    echo "[$(date)] 警告：数据库文件不存在: $DB_FILE"
    exit 1
fi

echo "[$(date)] 开始备份..."
cp "$DB_FILE" "$FILENAME"
echo "[$(date)] 备份完成：$FILENAME ($(du -sh "$FILENAME" | cut -f1))"

# 删除超过 KEEP_DAYS 天的旧备份
find "$BACKUP_DIR" -name "mold_db_*.db" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] 已清理 ${KEEP_DAYS} 天前的旧备份"
echo "[$(date)] 当前备份文件："
ls -lh "$BACKUP_DIR"/mold_db_*.db 2>/dev/null || echo "  （无）"
