#!/bin/bash

# Exit on error
set -e

# Update package index
echo "Updating package index..."
sudo apt-get update

# Install prerequisites
echo "Installing prerequisites..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
echo "Adding Docker's GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo "Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
sudo apt-get update

# Install Docker Engine
echo "Installing Docker Engine..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group and verify
echo "Adding current user to docker group..."
sudo usermod -aG docker $USER

# Verify group addition
if getent group docker | grep -q "\b${USER}\b"; then
    echo "Successfully added $USER to docker group"
else
    echo "Failed to add $USER to docker group. Retrying..."
    # Force group addition
    sudo gpasswd -a $USER docker
fi

# Print success message and instructions
echo "Docker installation completed successfully!"

# Start Docker service
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker installation and service status
echo "Docker version:"
docker --version

echo "Docker Compose version:"
docker compose version
