FROM python:3.10-slim AS base

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 && \
    rm -rf /var/lib/apt/lists/*

# Permission kludges to support `docker run --user xxx`
RUN mkdir       /.aider /app /.cache
RUN chmod a+rwx /.aider /app /.cache

# So git doesn't complain about unusual permissions
RUN git config --system --add safe.directory /app

# So pip installs work
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
