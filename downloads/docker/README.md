# Docker Setup

This repository contains a Dockerfile and scripts for setting up a Docker container.

## Prerequisites

Before you begin, make sure you have the following installed on your system:
- Docker

## Installation

To install the Dockerfile and scripts, follow these steps:

1. Download the `docker.zip` file from the [GitHub Releases](https://github.com/paul-gauthier/aider/releases) page.
2. Extract the contents of the `docker.zip` file to the project you want to use aider with.

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

This will start a Docker container from the `aider` image with 
* a user called dockeruser who has the same user id and group id as the current user (ie they can edit files as you).
* the current directory mounted into the `/app` directory in the container.
* the OPENAI_API_KEY environment variable copied over
* aider installed and available on the command line


Note: you may need to setup the git config in your project directory so aider won't be able to read your global git config
