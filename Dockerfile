FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    # prevent gh/git from prompting
    GIT_TERMINAL_PROMPT=0

# Rust + Foundry locations
ENV RUSTUP_HOME=/opt/rustup \
    CARGO_HOME=/opt/cargo \
    FOUNDRY_DIR=/opt/foundry
ENV PATH="/opt/cargo/bin:/opt/foundry/bin:${PATH}"

RUN apt-get update && apt-get install --no-install-recommends -y \
      ca-certificates curl git bash \
      build-essential pkg-config libssl-dev \
      pandoc libportaudio2 \
      # gh cli
      gh \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (minimal profile)
RUN curl -sSf https://sh.rustup.rs | bash -s -- -y --profile minimal \
    && mkdir -p /opt/cargo /opt/rustup \
    && cp -a /root/.cargo/* /opt/cargo/ \
    && cp -a /root/.rustup/* /opt/rustup/ \
    && rm -rf /root/.cargo /root/.rustup

# Install Foundry (forge)
RUN curl -L https://foundry.paradigm.xyz | bash \
    && /root/.foundry/bin/foundryup \
    && mkdir -p /opt/foundry \
    && cp -a /root/.foundry/* /opt/foundry/ \
    && rm -rf /root/.foundry

WORKDIR /app

COPY . /app

RUN python -m pip install --upgrade pip \
    && pip install -e .

RUN chmod +x /app/slm_cmd

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8080

CMD ["sh", "-lc", "uvicorn aider.slm:app --host ${HOST} --port ${PORT}"]
