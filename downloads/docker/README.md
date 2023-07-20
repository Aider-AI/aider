# Docker Setup

This repository contains a Dockerfile and scripts for setting up a Docker container.

## Prerequisites

Before you begin, make sure you have the following installed on your system:
- Docker

## Installation

To install the Dockerfile and scripts, follow these steps:

1. Download the `docker.zip` file from the [GitHub Releases](https://github.com/your-repo/releases) page.
2. Extract the contents of the `docker.zip` file.
3. Navigate to the `downloads/docker` directory.

## Building the Docker Image

To build the Docker image, run the following command:

```bash
./docker-build
```

This will build a Docker image named `aider`.

## Starting the Docker Container

To start the Docker container, run the following command:

```bash
./docker-start
```

This will start a Docker container from the `aider` image. The current directory will be mounted into the `/app` directory in the container.

