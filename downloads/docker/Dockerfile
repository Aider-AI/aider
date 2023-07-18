FROM ubuntu:latest

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y python3.11 python3-pip git universal-ctags sudo

# Create a directory for the app
RUN mkdir /app

# Install python packages
RUN pip3 install aider-chat

# Create the script
RUN echo '#!/bin/bash' > /create_user.sh && \
    echo 'groupadd -g $GID dockergrp' >> /create_user.sh && \
    echo 'useradd -u $UID -g $GID -m -s /bin/bash dockeruser' >> /create_user.sh && \
    echo 'su dockeruser' >> /create_user.sh && \
    echo 'exec "$@"' >> /create_user.sh && \
    chmod +x /create_user.sh && \
    /bin/bash

WORKDIR /app

# Use ENTRYPOINT to allow parameters to be passed in
ENTRYPOINT ["/bin/bash", "/create_user.sh"]
