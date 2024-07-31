FROM python:3.10-slim AS base

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /.aider && chmod a+rwx /.aider

# So git doesn't complain about unusual permissions with `docker run --user xxx`
RUN mkdir /app && chmod a+rwx /app && git config --system --add safe.directory /app

# So pip installs work even with `docker run --user xxx`
RUN chmod a+rwx /usr/local/lib/python3.10/site-packages /usr/local/*

WORKDIR /app

#########################
FROM base AS aider-full

COPY . /aider
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /aider[help,browser,playwright] \
       --extra-index-url https://download.pytorch.org/whl/cpu \
    && rm -rf /aider

RUN playwright install --with-deps chromium

ENTRYPOINT ["aider"]

#########################
FROM base AS aider

COPY . /aider
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /aider \
       --extra-index-url https://download.pytorch.org/whl/cpu \
    && rm -rf /aider

ENTRYPOINT ["aider"]
