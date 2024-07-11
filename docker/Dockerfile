FROM python:3.10-slim

COPY . /aider

# Unfortunately to build the multi-arch docker image we need `build-essential` for amd64.
# Apparently py-tree-sitter-languages doesn't have a pre-built binary wheel?
# Apparently Playwright needs build-essentials too.

RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential git libportaudio2 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir /aider[hf-embed] --extra-index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /aider
    
WORKDIR /app
ENTRYPOINT ["aider"]