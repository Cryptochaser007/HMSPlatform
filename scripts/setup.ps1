# ==============================================================================
# HMS Platform - Local Development Environment Bootstrap Script (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "Initialising ABDM-Enabled NABH HMS Platform..." -ForegroundColor Cyan

# 1. Copy .env if not exists
if (-not (Test-Path ".env")) {
    Write-Host "Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"

    # Generate 64-character hex secret key using native .NET cryptography
    $secretBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($secretBytes)
    $secretKey = [System.BitConverter]::ToString($secretBytes).Replace("-", "").ToLower()

    # Generate 32-byte URL-safe base64 Fernet encryption key using native .NET
    $fernetBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($fernetBytes)
    $encryptionKey = [Convert]::ToBase64String($fernetBytes).Replace('+', '-').Replace('/', '_')

    # Replace placeholders in .env
    $content = Get-Content ".env" -Raw
    $content = $content.Replace("replace_with_a_secure_random_64_character_hex_secret_key", $secretKey)
    $content = $content.Replace("replace_with_a_valid_fernet_base64_encoded_32_byte_key=", $encryptionKey)
    Set-Content ".env" $content -NoNewline
    Write-Host "Generated application SECRET_KEY and Fernet ENCRYPTION_KEY" -ForegroundColor Green
} else {
    Write-Host ".env already exists, keeping current configuration." -ForegroundColor Green
}

# 2. Start Infrastructure Containers if Docker is available
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Starting PostgreSQL, Redis, and Orthanc PACS containers..." -ForegroundColor Yellow
    docker compose up -d db redis orthanc
    Write-Host "Waiting for database container to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
} else {
    Write-Host "Docker was not found in PATH. Ensure PostgreSQL and Redis are running locally." -ForegroundColor DarkYellow
}

# 3. Virtual Environment Setup & Dedicated Pip Execution
$venvPath = ".\venv"
$venvPython = "$venvPath\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment in $venvPath..." -ForegroundColor Yellow
    try {
        python -m venv $venvPath
    } catch {
        Write-Host "Could not auto-create venv. Ensure Python 3.12+ is installed." -ForegroundColor DarkYellow
    }
}

if (Test-Path $venvPython) {
    Write-Host "Using virtual environment Python: $venvPython" -ForegroundColor Green
    Write-Host "Upgrading pip in virtual environment..." -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip

    Write-Host "Installing requirements into virtual environment..." -ForegroundColor Yellow
    & $venvPython -m pip install -r backend/requirements.txt

    Write-Host "Seeding initial master data..." -ForegroundColor Yellow
    & $venvPython scripts/seed_data.py
} else {
    # Fallback to system python
    Write-Host "Virtual environment not detected; falling back to system python..." -ForegroundColor Yellow
    try {
        python -m pip install --upgrade pip
        python -m pip install -r backend/requirements.txt
        python scripts/seed_data.py
    } catch {
        Write-Host "Pip or seed execution encountered an issue. Ensure your Python environment is active." -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "HMS Platform Setup Complete!" -ForegroundColor Green
Write-Host "   - API Swagger Docs: http://localhost:8000/docs"
Write-Host "   - Adminer DB GUI:   http://localhost:8080"
Write-Host "   - Orthanc PACS:     http://localhost:8042"
Write-Host ""
Write-Host "   Default Admin Credentials:"
Write-Host "   - Email:    admin@hms.local"
Write-Host "   - Password: Admin@123"
Write-Host "==============================================================================" -ForegroundColor Green
