FROM python:3.10-slim AS base

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS aider-full

COPY . /aider
RUN pip install --no-cache-dir /aider[help,browser] --extra-index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /aider

ENTRYPOINT ["aider"]

FROM base AS aider

COPY . /aider
RUN pip install --no-cache-dir /aider --extra-index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /aider

ENTRYPOINT ["aider"]
