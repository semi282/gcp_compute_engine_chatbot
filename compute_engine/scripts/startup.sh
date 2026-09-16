#!/bin/bash
set -e

LOG_FILE="/var/log/chatbot_startup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=================================================="
echo " Starting The Herbwitch Chatbot VM Setup"
echo " Time: $(date)"
echo "=================================================="

# 1. Update and install system dependencies
apt-get update -y
apt-get install -y python3 python3-pip python3-venv curl git jq

# 2. Create application directory
APP_DIR="/opt/chatbot"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 3. Create Python virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi

# 4. Fetch GEMINI_API_KEY from Secret Manager using VM instance identity
echo "[SecretManager] Fetching GEMINI_API_KEY..."
SECRET_NAME="projects/352439210179/secrets/GEMINI_API_KEY/versions/latest"
METADATA_TOKEN_URL="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

ACCESS_TOKEN=$(curl -s -H "Metadata-Flavor: Google" "$METADATA_TOKEN_URL" | jq -r '.access_token')
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    SECRET_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://secretmanager.googleapis.com/v1/$SECRET_NAME:access")
    GEMINI_KEY=$(echo "$SECRET_RESPONSE" | jq -r '.payload.data' | base64 --decode)
    if [ -n "$GEMINI_KEY" ] && [ "$GEMINI_KEY" != "null" ]; then
        echo "GEMINI_API_KEY=$GEMINI_KEY" > "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"
        echo "[SecretManager] Successfully retrieved and stored GEMINI_API_KEY"
    else
        echo "[SecretManager] Warning: Could not decode secret payload"
    fi
else
    echo "[SecretManager] Warning: Could not obtain VM access token"
fi

# 5. Enable and start systemd service if code is in place
if [ -f "$APP_DIR/app.py" ]; then
    "$APP_DIR/venv/bin/pip" install --upgrade pip
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    systemctl daemon-reload
    systemctl enable chatbot.service
    systemctl restart chatbot.service
    echo "[Service] Chatbot service started successfully!"
fi

echo "=================================================="
echo " VM Setup Script Complete: $(date)"
echo "=================================================="
