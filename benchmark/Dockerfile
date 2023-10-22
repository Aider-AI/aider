FROM python:3.10-slim
RUN apt-get update && apt-get install -y less git build-essential
COPY requirements.txt /aider/requirements.txt
RUN pip install --upgrade pip
RUN pip install lox typer pandas matplotlib imgcat aider-chat
RUN pip install -r /aider/requirements.txt
RUN git config --global --add safe.directory /aider
WORKDIR /aider
