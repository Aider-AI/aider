FROM python:3.10-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY . /aider
RUN pip install --upgrade pip && pip install /aider
WORKDIR /app
ENTRYPOINT ["aider"]


