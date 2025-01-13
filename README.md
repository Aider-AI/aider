<!-- Edit README.md, not index.md -->

# Aider REST API - AI Pair Programming as a Service

This fork of Aider focuses on providing a REST API interface to Aider's powerful AI pair programming capabilities. While maintaining all the original CLI features, it adds a robust API layer that allows you to integrate Aider's functionality into your own applications and services.

<p align="center">
  <a href="https://discord.gg/Tv2uQnR88V">
    <img src="https://img.shields.io/badge/Join-Discord-blue.svg"/>
  </a>
  <a href="https://aider.chat/docs/install.html">
    <img src="https://img.shields.io/badge/Read-Docs-green.svg"/>
  </a>
</p>

## REST API

Aider's REST API allows you to integrate AI pair programming capabilities into your applications. The API server can be started using:

```bash
python -m aider.server [aider_args]
```

For example, here's an advanced configuration using multiple models and features:
```bash
python -m aider.server --architect --model openrouter/anthropic/claude-3.5-sonnet:beta --editor-model openrouter/anthropic/claude-3.5-sonnet --weak-model claude-3-haiku-20240307 --cache-prompts --analytics
```

The server runs on `http://0.0.0.0:8000` by default and provides the following endpoints:

### POST /init
Initializes an Aider instance with the provided configuration.

Request body:
```json
{
    "pretty": false  // Optional, defaults to false
}
```

### POST /chat
Sends a message to chat with Aider.

Request body:
```json
{
    "content": "Your message here"
}
```

Response includes an array of responses with different types:
- tool_output: Results from tool operations
- error: Error messages
- warning: Warning messages
- print: General output messages
- system: System messages
- assistant: AI assistant responses

### POST /stop
Stops the Aider instance.

## Acknowledgment

A special thanks to Paul Gauthier, the original creator of Aider. His innovative work in developing Aider as an AI pair programming tool has revolutionized how developers interact with AI assistants. This REST API fork builds upon his excellent foundation to extend Aider's capabilities to even more use cases.
