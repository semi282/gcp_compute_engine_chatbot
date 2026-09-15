#!/bin/bash
set -e

echo "=== 1. Installing Nginx and Certbot ==="
apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx openssl

echo "=== 2. Generating High-Security OpenSSL SAN SSL Certificate ==="
mkdir -p /etc/ssl/certs /etc/ssl/private

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/chatbot.key \
  -out /etc/ssl/certs/chatbot.crt \
  -subj "/CN=136.65.198.112/O=The Herbwitch Academy/C=KR" \
  -addext "subjectAltName=IP:136.65.198.112,DNS:136-65-198-112.sslip.io,DNS:136.65.198.112.nip.io,DNS:localhost"

chmod 600 /etc/ssl/private/chatbot.key
chmod 644 /etc/ssl/certs/chatbot.crt

echo "=== 3. Creating Nginx Configuration with SSL and SSE Streaming Optimizations ==="
cat << 'EOF' > /etc/nginx/sites-available/chatbot
# HTTP: Redirect all port 80 traffic to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS: Standard port 443 & port 5000 with SSL
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    listen 5000 ssl;
    listen [::]:5000 ssl;
    server_name _;

    ssl_certificate /etc/ssl/certs/chatbot.crt;
    ssl_certificate_key /etc/ssl/private/chatbot.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Critical optimizations for Server-Sent Events (SSE) streaming
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot

echo "=== 4. Testing and Restarting Nginx ==="
nginx -t
systemctl daemon-reload
systemctl enable nginx
systemctl restart nginx

echo "=== 5. Attempting Let's Encrypt Certificate for 136-65-198-112.sslip.io ==="
certbot --nginx -d 136-65-198-112.sslip.io --non-interactive --agree-tos --register-unsafely-without-email || echo "Let's Encrypt notice: Fallback to OpenSSL SAN certificate active."

systemctl reload nginx
echo "=== HTTPS Setup Complete! ==="
