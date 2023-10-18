FROM python:3.10-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir /aider && rm -rf /aider
WORKDIR /app
ENTRYPOINT ["aider"]
