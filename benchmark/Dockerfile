FROM python:3.10-slim
RUN apt-get update
RUN apt-get install -y less git build-essential
COPY . /aider
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -e /aider[dev]
RUN git config --global --add safe.directory /aider
WORKDIR /aider
