#!/bin/bash

# Build the Docker image
docker build -t my-jekyll-site -f scripts/Dockerfile.jekyll .
