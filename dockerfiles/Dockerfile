FROM python:3.10

ARG UID
ARG GID

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y python3.11 python3-pip git universal-ctags sudo

# Create a directory for the app
RUN mkdir /app
RUN mkdir -p /src/aider

# Install python packages
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the application to container. This can be overridden when running.
COPY aider /src/aider

# Add user to the container
RUN groupadd -g $GID dockergrp \
    && useradd -u $UID -g $GID -m -s /bin/bash dockeruser \
    && echo dockeruser ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dockeruser \
    && chmod 0440 /etc/sudoers.d/dockeruser

ENV PYTHONPATH=/src
ENV PYTHONDONTWRITEBYTECODE=YES

USER dockeruser

WORKDIR /app

# Use ENTRYPOINT to allow parameters to be passed in
#ENTRYPOINT ["bin/bash"]
ENTRYPOINT ["python3", "/src/aider/main.py"]
