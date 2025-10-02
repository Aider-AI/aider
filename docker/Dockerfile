FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 pandoc wget fonts-unifont fontconfig  && \
    wget -O /tmp/fonts-ubuntu.deb http://ftp.de.debian.org/debian/pool/non-free/f/fonts-ubuntu/fonts-ubuntu_0.83-6_all.deb && \
    wget -O /tmp/ttf-unifont.deb http://ftp.de.debian.org/debian/pool/main/u/unifont/ttf-unifont_13.0.06-1_all.deb && \
    wget -O /tmp/ttf-ubuntu-font-family.deb http://ftp.de.debian.org/debian/pool/non-free/f/fonts-ubuntu/ttf-ubuntu-font-family_0.83-4_all.deb && \
    dpkg -i /tmp/fonts-ubuntu.deb /tmp/ttf-unifont.deb /tmp/ttf-ubuntu-font-family.deb && \
    apt-get install -f -y && \
    rm /tmp/fonts-ubuntu.deb /tmp/ttf-unifont.deb /tmp/ttf-ubuntu-font-family.deb && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/* && \    
    rm -rf /var/lib/apt/lists/*

# Create app user with UID 1000
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Create virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN /venv/bin/python -m pip install --no-cache-dir uv

# Playwright browser settings
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/pw-browsers
ENV PLAYWRIGHT_SKIP_BROWSER_GC=1

# Create directories with proper permissions
RUN mkdir -p /home/appuser/.aider /home/appuser/.cache /home/appuser/pw-browsers && \
    chown -R appuser:appuser /home/appuser /app /venv && \
    chmod -R 777 /home/appuser/.aider /home/appuser/.cache /home/appuser/pw-browsers

# So git doesn't complain about unusual permissions
RUN git config --system --add safe.directory /app

# This puts the container's ~/.aider into the host's project directory (usually host's cwd).
# That way caches, version checks, etc get stored in the host filesystem not
# simply discarded every time the container exits.
ENV HOME=/app

#########################
FROM base AS aider-ce

ENV AIDER_DOCKER_IMAGE=dustinwashington/aider-ce

# Copy requirements files
COPY requirements.txt /tmp/aider/
COPY requirements/ /tmp/aider/requirements/

# Install dependencies as root
RUN uv pip install --no-cache-dir -r /tmp/aider/requirements.txt && \
    rm -rf /tmp/aider

# Install playwright browsers
RUN uv pip install --no-cache-dir playwright && \
    /venv/bin/python -m playwright install --with-deps chromium

# Fix site-packages permissions
RUN find /venv/lib/python3.12/site-packages \( -type d -exec chmod a+rwx {} + \) -o \( -type f -exec chmod a+rw {} + \)

# Copy the rest of the application code
COPY . /app/

# Install the application as a package
RUN uv pip install . && \
    find . -mindepth 1 -delete

# Switch to appuser
USER appuser

ENTRYPOINT ["/venv/bin/aider"]
