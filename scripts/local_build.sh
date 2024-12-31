#!/bin/bash

# Exit on error
set -e

# Get version from Dockerfile (includes OS suffix)
DOCKER_VERSION=$(python3 scripts/docker_version.py)
DOCKER_IMAGE="ghcr.io/caseymcc/aider/builder:${DOCKER_VERSION}"

echo "Checking for Docker image: ${DOCKER_IMAGE}"

# Try to pull the image from GitHub Container Registry
if docker pull ${DOCKER_IMAGE} >/dev/null 2>&1; then
    echo "Found existing Docker image, using it for build"
else
    echo "Building Docker image locally..."
    docker build -t ${DOCKER_IMAGE} -f scripts/Dockerfile.cio .
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Run the build in Docker
echo "Running build in Docker container..."
docker run --rm \
    -v "$(pwd):/repo" \
    -v "$(pwd)/dist:/repo/dist" \
    ${DOCKER_IMAGE}

echo "Build complete! Executable should be in dist/"
