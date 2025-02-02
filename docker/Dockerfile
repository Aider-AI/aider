FROM python:3.12-slim AS base

# Create non-root user first
RUN useradd -m -u 1000 -s /bin/bash appuser
ENV HOME=/home/appuser

RUN mkdir -p \
    $HOME/.aider \
    $HOME/.cache \
    $HOME/pw-browsers \
    $HOME/app \
    $HOME/venv


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libportaudio2 \
    pandoc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR $HOME/app

# Set up Python environment and Playwright settings
ENV PATH="$HOME/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers \
    PLAYWRIGHT_SKIP_BROWSER_GC=1

RUN python -m venv $HOME/venv && \
    pip install --no-cache-dir --upgrade pip

COPY --chown=appuser:appuser . $HOME/aider

RUN git config --global --add safe.directory $HOME/app

#########################
FROM base AS aider-full

ENV AIDER_DOCKER_IMAGE=paulgauthier/aider-full

# Install extra dependencies
RUN pip install --no-cache-dir $HOME/aider[playwright,help,browser] \
    --extra-index-url https://download.pytorch.org/whl/cpu && \
    playwright install --with-deps chromium

RUN rm -rf $HOME/aider

RUN chown -R appuser:appuser $HOME

USER appuser

ENTRYPOINT ["aider"]

#########################
FROM base AS aider

ENV AIDER_DOCKER_IMAGE=paulgauthier/aider

RUN pip install --no-cache-dir $HOME/aider[playwright] \
    --extra-index-url https://download.pytorch.org/whl/cpu && \
    playwright install --with-deps chromium

RUN rm -rf $HOME/aider

RUN chown -R appuser:appuser $HOME

USER appuser

ENTRYPOINT ["aider"]
