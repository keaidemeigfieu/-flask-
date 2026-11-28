#!/usr/bin/env bash
# 一键部署/更新脚本：备份 -> 装依赖 -> 加载环境变量 -> 建表 -> nginx 提示 -> 重启服务
# 用法：在 Linux 服务器项目目录下执行  bash deploy.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
VENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="${SERVICE_NAME:-simplechat}"   # systemd 服务名，可用环境变量覆盖

echo "==> 项目目录: $APP_DIR"

# 1. 备份数据库（会提示输入数据库密码）
echo "[1/6] 备份数据库..."
if command -v mysqldump >/dev/null 2>&1; then
  STAMP=$(date +%F-%H%M%S)
  if mysqldump --no-tablespaces -u chat_user -p chat_db > "$APP_DIR/backup_$STAMP.sql" 2>/dev/null; then
    echo "      备份完成: backup_$STAMP.sql"
  else
    echo "      备份失败（请检查账号密码），继续..."
  fi
else
  echo "      未安装 mysqldump，跳过备份"
fi

# 2. 安装依赖
echo "[2/6] 安装依赖..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -r "$APP_DIR/requirements.txt" gunicorn

# 3. 加载环境变量
echo "[3/6] 加载环境变量..."
if [ -f "$APP_DIR/.env" ]; then
  set -a; . "$APP_DIR/.env"; set +a
  echo "      已读取 $APP_DIR/.env"
else
  echo "      警告: 未找到 .env，请先创建（参考 .env.example）"
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "      错误: DATABASE_URL 未设置，无法连库。中止。"
  exit 1
fi
if [ -z "${SECRET_KEY:-}" ]; then
  SECRET_KEY=$("$VENV_DIR/bin/python" -c "import secrets;print(secrets.token_hex(32))")
  export SECRET_KEY
  echo "      已生成随机 SECRET_KEY（多 worker 安全，建议写入 .env 固定下来）"
fi

# 4. 建表（幂等：缺表建表，缺列加列，兼容旧库）
echo "[4/6] 检查/创建数据库表..."
"$VENV_DIR/bin/python" - "$APP_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    db.create_all()  # 只创建缺失的表，已存在的跳过
    insp = inspect(db.engine)
    if 'posts' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('posts')}
        if 'video' not in cols:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN video VARCHAR(200)'))
            db.session.commit()
            print('      已为 posts 表补充 video 列')
    print('      表结构就绪')
PY

# 5. nginx 提示
echo "[5/6] 提示: 若需上传视频，请确认 nginx 配置了 client_max_body_size 100m;"
echo "      并确保 static/uploads 目录对运行用户可写。"

# 6. 重启服务
echo "[6/6] 重启服务..."
if systemctl list-unit-files "$SERVICE_NAME.service" >/dev/null 2>&1; then
  sudo systemctl restart "$SERVICE_NAME"
  echo "      已重启 systemd 服务: $SERVICE_NAME"
else
  echo "      未找到 systemd 服务 '$SERVICE_NAME'，请手动启动："
  echo "      $VENV_DIR/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app"
fi

echo "==> 完成。请打开浏览器验证：登录、发动态(带emoji)、上传视频、关注+通知。"
