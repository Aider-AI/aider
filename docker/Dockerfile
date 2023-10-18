FROM python:3.10-slim
COPY . /aider
RUN apt-get update && \
    apt-get install --no-install-recommends -y git universal-ctags libportaudio2 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir /aider && \
    rm -rf /aider
WORKDIR /app
ENTRYPOINT ["aider"]
