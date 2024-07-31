FROM python:3.10-slim AS base

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# So git doesn't complain about unusual permissions
RUN git config --system --add safe.directory /app

#########################
FROM base AS aider-full

COPY . /tmp/aider
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /tmp/aider[help,browser,playwright] \
       --extra-index-url https://download.pytorch.org/whl/cpu \
    && rm -rf /tmp/aider

RUN playwright install --with-deps chromium

ENTRYPOINT ["/venv/bin/aider"]

#########################
FROM base AS aider

COPY . /tmp/aider
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /tmp/aider \
       --extra-index-url https://download.pytorch.org/whl/cpu \
    && rm -rf /tmp/aider

ENTRYPOINT ["/venv/bin/aider"]
