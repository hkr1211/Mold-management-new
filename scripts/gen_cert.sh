#!/bin/sh
# scripts/gen_cert.sh — 生成自签名 TLS 证书（开发/内网部署用）
#
# 生产环境建议使用 Let's Encrypt (certbot) 替换此证书。
# 用法：sh scripts/gen_cert.sh [域名或IP，默认 localhost]

set -e

DOMAIN="${1:-localhost}"
OUT_DIR="nginx/ssl"
DAYS=3650  # 10 年

mkdir -p "$OUT_DIR"

echo "→ 为 ${DOMAIN} 生成自签名证书（有效期 ${DAYS} 天）..."

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "${OUT_DIR}/server.key" \
  -out    "${OUT_DIR}/server.crt" \
  -days   "$DAYS" \
  -subj   "/C=CN/ST=Shanghai/L=Shanghai/O=YunJie/CN=${DOMAIN}" \
  -addext "subjectAltName=DNS:${DOMAIN},IP:127.0.0.1"

chmod 600 "${OUT_DIR}/server.key"
echo "✅ 证书已生成："
echo "   证书: ${OUT_DIR}/server.crt"
echo "   私钥: ${OUT_DIR}/server.key"
echo ""
echo "提示：浏览器首次访问会提示「不受信任」，点击「高级 → 继续访问」即可。"
echo "生产环境请使用 Let's Encrypt：https://certbot.eff.org/"
