# Build stage
FROM python:3.10-slim AS builder

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git

COPY . /aider

RUN    pip install --no-cache-dir /aider
RUN    pip install --no-cache-dir /aider[hf-embed] --extra-index-url https://download.pytorch.org/whl/cpu

# Final stage
FROM python:3.10-slim
RUN apt-get update && \
    apt-get install --no-install-recommends -y git libportaudio2 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/aider /usr/local/bin/aider

WORKDIR /app
ENTRYPOINT ["aider"]
