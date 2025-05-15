#!/bin/bash
set -e

echo "Setting up WiMi Backend development environment..."

# Parse command line arguments
DEV_MODE=false
for arg in "$@"
do
    case $arg in
        --dev)
        DEV_MODE=true
        shift
        ;;
    esac
done

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python12 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ "$DEV_MODE" = true ]; then
    echo "Installing development dependencies..."
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    else
        echo "WARNING: requirements-dev.txt not found. Skipping development dependencies."
    fi
fi

# Application Settings
ENVIRONMENT=development
PORT=8000
LOG_LEVEL=INFO
DEBUG=True

echo "Make sure to setup the .env file before running the application"
echo "Setup complete! You can now run the application with:"
echo "source venv/bin/activate && python run.py" 