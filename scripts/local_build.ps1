# Exit on error
$ErrorActionPreference = "Stop"

$CONFIG_FILE = "scripts/build_config.json"

if (-not (Test-Path $CONFIG_FILE)) {
    Write-Error "Error: build_config.json not found"
    exit 1
}

# Read config file for Python version
$config = Get-Content $CONFIG_FILE | ConvertFrom-Json

# Check if pyenv-win is installed
$pyenvPath = "$env:USERPROFILE\.pyenv\pyenv-win"
if (-not (Test-Path $pyenvPath)) {
    Write-Host "Installing pyenv-win..."
    Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"
    & ./install-pyenv-win.ps1
    Remove-Item ./install-pyenv-win.ps1
    
    # Set up environment variables
    $env:PYENV = "$env:USERPROFILE\.pyenv\pyenv-win"
    $env:Path = "$env:PYENV\bin;$env:PYENV\shims;$env:Path"
}

# Get Python version from config
$pythonVersion = $config.python_version

# Install Python version if not present
$installedVersions = & pyenv versions
if ($installedVersions -notcontains $pythonVersion) {
    Write-Host "Installing Python $pythonVersion..."
    & pyenv install $pythonVersion
}

# Set local Python version and create venv
Write-Host "Setting up Python virtual environment..."
& pyenv local $pythonVersion
python -m venv venv
. .\venv\Scripts\Activate.ps1

# Run the Python build script
python scripts/build.py

# Deactivate virtual environment
deactivate
