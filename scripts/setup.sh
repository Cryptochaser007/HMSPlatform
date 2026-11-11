#!/usr/bin/env bash
# ==============================================================================
# HMS Platform - Local Development Environment Bootstrap Script (Linux/macOS)
# ==============================================================================
set -e

echo "🏥 Initializing ABDM-Enabled NABH HMS Platform..."

# 1. Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.12+ is required."; exit 1; }

# 2. Setup .env file
if [ ! -f .env ]; then
    echo "📋 Copying .env.example to .env..."
    cp .env.example .env
    
    # Generate random secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Replace in .env
    sed -i.bak "s/replace_with_a_secure_random_64_character_hex_secret_key/$SECRET_KEY/" .env
    sed -i.bak "s|replace_with_a_valid_fernet_base64_encoded_32_byte_key=|$ENCRYPTION_KEY|" .env
    rm -f .env.bak
    echo "🔑 Generated application SECRET_KEY and Fernet ENCRYPTION_KEY"
fi

# 3. Start Infrastructure Containers
echo "🐳 Starting PostgreSQL, Redis, and Orthanc PACS containers..."
docker compose up -d db redis orthanc

# 4. Wait for database readiness
echo "⏳ Waiting for PostgreSQL database to accept connections..."
until docker compose exec db pg_isready -U hms_user -d hms_db; do
  sleep 2
done

# 5. Virtualenv & Dependencies
echo "📦 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 6. Database Migrations & Seeding
echo "🌱 Running database initialization and seeding master records..."
python scripts/seed_data.py

echo ""
echo "=============================================================================="
echo "🎉 HMS Platform is successfully initialized!"
echo "   - API Swagger Docs: http://localhost:8000/docs"
echo "   - Adminer DB GUI:   http://localhost:8080"
echo "   - Orthanc PACS:     http://localhost:8042"
echo ""
echo "   Default Admin Credentials:"
echo "   - Email:    admin@hms.local"
echo "   - Password: Admin@123"
echo "=============================================================================="

