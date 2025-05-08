---
parent: Connecting to LLMs
nav_order: 500
---

# OpenAI compatible APIs

Aider can connect to any LLM which is accessible via an OpenAI compatible API endpoint.

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=<endpoint>
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE <endpoint>
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and your OpenAI compatible API on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/<model-name>
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

Example:    
Here's a simplified example demonstrating how to request LLM server deployed using SGLang via an OpenAI compatible API endpoint.
   
Step 1: Launch the SGLang server   
In this example, we use the [Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) model. For demonstration purposes, the SGLang server is launched locally. After installing SGLang, or within an [SGLang docker container](https://hub.docker.com/r/lmsysorg/sglang/tags), before starting the server, ensure that the model checkpoints are available in your huggingface cache directory, or that you have authenticated with huggingface tokens. Then you can start the server using the following command:
```
python3 -m sglang.launch_server --model-path meta-llama/Llama-3.1-8B-Instruct --host 0.0.0.0 --port 30000
```


Step 2: modify API endpoint and run aider
```bash
# Mac/Linux:
Export OPENAI_API_BASE=http://localhost:30000/v1
Export OPENAI_API_KEY=None

# Change directory into your codebase
cd /to/your/project

aider --model openai/meta-llama/Llama-3.1-8B-Instruct
```
