#!/bin/bash
# 途迹 TripCanvas 部署脚本
# 用法: bash deploy.sh
set -e

cd ~/trip

echo "=== 1. 构建后端镜像 ==="
docker compose build backend

echo "=== 2. 创建数据库（如不存在） ==="
docker exec news-mysql mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS trip_canvas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true

echo "=== 3. 初始化数据库表 ==="
docker compose run --rm backend python init_db.py || echo "init_db 跳过（表可能已存在）"

echo "=== 4. 启动后端 ==="
docker compose up -d backend

echo "=== 5. 等待后端启动 ==="
sleep 3
docker ps --format '{{.Names}} {{.Status}}' | grep trip-backend

echo "=== 6. 健康检查 ==="
curl -s http://127.0.0.1:8002/api/health || echo "健康检查失败"

echo ""
echo "=== 部署完成 ==="
echo "前端: http://82.156.177.145:8081"
echo "后端: http://127.0.0.1:8002"
