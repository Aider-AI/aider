FROM ubuntu:latest

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y python3.11 python3-pip git universal-ctags sudo

# Create a directory for the app
RUN mkdir /app
RUN mkdir -p /src/aider

# Install python packages
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Create the script
RUN echo '#!/bin/bash' > /create_user.sh && \
    echo 'groupadd -g $GID dockergrp' >> /create_user.sh && \
    echo 'useradd -u $UID -g $GID -m -s /bin/bash dockeruser' >> /create_user.sh && \
    echo 'su dockeruser -c /usr/bin/bash <<EOF' >> /create_user.sh && \
    echo 'echo "$@"' >> /create_user.sh && \
    echo 'exec <>/dev/tty $@' >> /create_user.sh && \
    echo 'EOF' >> /create_user.sh && \
    chmod +x /create_user.sh && \
    cat /create_user.sh 

ENV PYTHONPATH=/src
ENV PYTHONDONTWRITEBYTECODE=YES

WORKDIR /app

# Use ENTRYPOINT to allow parameters to be passed in
#ENTRYPOINT ["/bin/bash"]
#ENTRYPOINT ["/create_user.sh"]
ENTRYPOINT ["python3", "/src/aider/main.py"]
