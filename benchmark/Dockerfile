FROM python:3.10-slim
RUN apt-get update
RUN apt-get install -y less git build-essential
COPY requirements.txt /aider/requirements.txt
COPY dev-requirements.txt /aider/dev-requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /aider/requirements.txt
RUN pip install -r /aider/dev-requirements.txt
RUN git config --global --add safe.directory /aider
WORKDIR /aider
