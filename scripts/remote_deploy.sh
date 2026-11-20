#!/usr/bin/env bash
# 在服务器上执行：安装后端依赖并重启服务。
# 前端应已由 CI 构建好并同步到 frontend/dist。
# 不触碰 backend/data 与 backend/.env
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/opt/kb}"
cd "$DEPLOY_PATH"

echo "==> deploy path: $DEPLOY_PATH"

if [[ ! -f frontend/dist/index.html ]]; then
  echo "ERROR: frontend/dist missing. Build frontend in CI before syncing." >&2
  exit 1
fi

# 后端 venv + 依赖
if [[ ! -d backend/.venv ]]; then
  echo "==> creating Python venv..."
  python3 -m venv backend/.venv
fi
echo "==> pip install..."
backend/.venv/bin/pip install -U pip wheel
backend/.venv/bin/pip install -r backend/requirements.txt

# 确保数据目录存在，但绝不删除已有内容
mkdir -p backend/data/uploads backend/data/chroma

# Nginx 站点（若尚未配置则写入）
if [[ ! -f /etc/nginx/sites-available/kb ]]; then
  cat >/etc/nginx/sites-available/kb <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 50m;
    root /opt/kb/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX
  rm -f /etc/nginx/sites-enabled/default
  ln -sfn /etc/nginx/sites-available/kb /etc/nginx/sites-enabled/kb
fi

# systemd unit
if [[ ! -f /etc/systemd/system/kb.service ]]; then
  cat >/etc/systemd/system/kb.service <<'UNIT'
[Unit]
Description=KB FastAPI backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/kb/backend
Environment=PATH=/opt/kb/backend/.venv/bin:/usr/bin
ExecStart=/opt/kb/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=3
MemoryMax=600M

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable kb
fi

nginx -t
systemctl reload nginx || systemctl restart nginx
systemctl restart kb
sleep 4
systemctl is-active kb
curl -sfS http://127.0.0.1:8000/api/health
echo
echo "==> deploy done"
