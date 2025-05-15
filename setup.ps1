# WiMi Backend Setup Script for Windows
Write-Host "Setting up WiMi Backend development environment..." -ForegroundColor Green

# Parse command line arguments
param (
    [switch]$Dev = $false
)

# Create virtual environment if it doesn't exist
if (-not (Test-Path -Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python3.12 -m venv venv
    Write-Host "Virtual environment created." -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ($Dev) {
    Write-Host "Installing development dependencies..." -ForegroundColor Cyan
    if (Test-Path -Path "requirements-dev.txt") {
        python -m pip install -r requirements-dev.txt
    } else {
        Write-Host "WARNING: requirements-dev.txt not found. Skipping development dependencies." -ForegroundColor Yellow
    }
}

# Application Settings
$env:ENVIRONMENT = "development"
$env:PORT = "8000"
$env:LOG_LEVEL = "INFO"
$env:DEBUG = "True"

Write-Host "Make sure to setup the .env file before running the application" -ForegroundColor Yellow
Write-Host "Setup complete! You can now run the application with:" -ForegroundColor Green
Write-Host ".\venv\Scripts\Activate.ps1; python run.py" -ForegroundColor Cyan 