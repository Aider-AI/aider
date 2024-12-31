# Exit on error
$ErrorActionPreference = "Stop"

# Get version from Dockerfile
$DOCKER_VERSION = python scripts/docker_version.py
$DOCKER_IMAGE = "ghcr.io/caseymcc/aider/builder:${DOCKER_VERSION}"

Write-Host "Checking for Docker image: ${DOCKER_IMAGE}"

# Try to pull the image from GitHub Container Registry
try {
    docker pull ${DOCKER_IMAGE} 2>$null
    Write-Host "Found existing Docker image, using it for build"
}
catch {
    Write-Host "Building Docker image locally..."
    docker build -t ${DOCKER_IMAGE} -f scripts/Dockerfile.windows.cio .
}

# Create dist directory if it doesn't exist
if (-not (Test-Path dist)) {
    New-Item -ItemType Directory -Path dist
}

# Run the build in Docker
Write-Host "Running build in Docker container..."
docker run --rm `
    -v "${PWD}:/repo" `
    -v "${PWD}/dist:/repo/dist" `
    ${DOCKER_IMAGE}

Write-Host "Build complete! Executable should be in dist/"
