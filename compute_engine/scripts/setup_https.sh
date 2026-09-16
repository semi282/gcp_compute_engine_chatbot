#!/bin/bash
set -e

echo "=== 1. Installing Nginx and Certbot ==="
apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx openssl

echo "=== 2. Detecting External IP & Generating SSL Certificate ==="
# Detect external IP dynamically from GCP metadata server, or fallback to argument / ifconfig.me
EXTERNAL_IP="${1:-}"
if [ -z "$EXTERNAL_IP" ]; then
    EXTERNAL_IP=$(curl -s -f -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" 2>/dev/null || true)
fi
if [ -z "$EXTERNAL_IP" ]; then
    EXTERNAL_IP=$(curl -s -f https://ifconfig.me 2>/dev/null || curl -s -f https://api.ipify.org 2>/dev/null || echo "127.0.0.1")
fi

IP_DASH=$(echo "$EXTERNAL_IP" | tr '.' '-')
echo "External IP detected: $EXTERNAL_IP ($IP_DASH.sslip.io)"

mkdir -p /etc/ssl/certs /etc/ssl/private

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/chatbot.key \
  -out /etc/ssl/certs/chatbot.crt \
  -subj "/CN=${EXTERNAL_IP}/O=The Herbwitch Academy/C=KR" \
  -addext "subjectAltName=IP:${EXTERNAL_IP},DNS:${IP_DASH}.sslip.io,DNS:${EXTERNAL_IP}.nip.io,DNS:localhost"

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

echo "=== 5. Attempting Let's Encrypt Certificate for ${IP_DASH}.sslip.io ==="
if [ "$EXTERNAL_IP" != "127.0.0.1" ]; then
    certbot --nginx -d "${IP_DASH}.sslip.io" --non-interactive --agree-tos --register-unsafely-without-email || echo "Let's Encrypt notice: Fallback to OpenSSL SAN certificate active."
else
    echo "Localhost detected, skipping Let's Encrypt."
fi

systemctl reload nginx
echo "=== HTTPS Setup Complete! ==="
