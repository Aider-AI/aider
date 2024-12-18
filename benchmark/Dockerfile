FROM buildpack-deps:jammy

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Go
RUN curl -OL https://golang.org/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Install Rust
ADD https://sh.rustup.rs /tmp/rustup.sh
RUN chmod +x /tmp/rustup.sh && /tmp/rustup.sh -y && rm /tmp/rustup.sh
ENV PATH="/root/.cargo/bin:${PATH}"

COPY . /aider
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -e /aider[dev]
RUN git config --global --add safe.directory /aider
WORKDIR /aider
