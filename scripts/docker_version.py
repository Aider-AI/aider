#!/usr/bin/env python3

def get_docker_version():
    """Extract version from Dockerfile."""
    with open("scripts/Dockerfile.cio", "r") as f:
        for line in f:
            if "LABEL version=" in line:
                return line.split("=")[1].strip().strip('"')
    return None

if __name__ == "__main__":
    version = get_docker_version()
    if version:
        print(version)
