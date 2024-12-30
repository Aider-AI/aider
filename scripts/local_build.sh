#!/bin/bash

# Exit on error
set -e

CONFIG_FILE="scripts/build_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: build_config.json not found"
    exit 1
fi

# Setup pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Install pyenv if not present
if [ ! -d "$PYENV_ROOT" ]; then
    echo "Installing pyenv..."
    curl https://pyenv.run | bash
fi

# Initialize pyenv
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Get Python version from config
PYTHON_VERSION=$(jq -r '.python_version' "$CONFIG_FILE")

# Install Python version if not present
if ! pyenv versions | grep -q $PYTHON_VERSION; then
    echo "Installing Python $PYTHON_VERSION..."
    pyenv install $PYTHON_VERSION
fi

# Set local Python version and create venv
echo "Setting up Python virtual environment..."
pyenv local $PYTHON_VERSION
python -m venv venv
source venv/bin/activate

# Run the Python build script
python scripts/build.py

# Deactivate virtual environment
deactivate
