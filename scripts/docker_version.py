#!/usr/bin/env python3

import platform
import sys

def get_docker_version():
    """Extract version from Dockerfile."""
    dockerfile = "scripts/Dockerfile.windows.cio" if sys.platform.startswith('win') else "scripts/Dockerfile.linux.cio"
    with open(dockerfile, "r") as f:
        for line in f:
            if "LABEL version=" in line:
                return line.split("=")[1].strip().strip('"')
    return None

def get_os_suffix():
    if sys.platform.startswith('win'):
        return "windows"
    elif sys.platform.startswith('darwin'):
        return "macos"
    else:
        return "linux"

if __name__ == "__main__":
    version = get_docker_version()
    if version:
        print(f"{version}-{get_os_suffix()}")
