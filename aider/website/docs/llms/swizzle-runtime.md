---
parent: Connecting to LLMs
nav_order: 515
---

# Swizzle Runtime

Aider can connect to [Swizzle Runtime](https://github.com/Swizzle-AI/swizzle-runtime) (`swizzle-rt`), an Apache-2.0, pure-Rust GGUF inference server with AVX2, NVIDIA CUDA (`sm_75` to `sm_120`), and Vulkan compute kernels.

First, install `swizzle-rt` on Linux x86_64 (CUDA 12.8) or build from source:

```bash
curl -fsSL https://raw.githubusercontent.com/Swizzle-AI/swizzle-runtime/main/install.sh | sh
```

Pull a local GGUF model and start the OpenAI-compatible server:

```bash
swizzle-rt pull Qwen/Qwen3-0.6B-GGUF:Q8_0
swizzle-rt serve Qwen3-0.6B-Q8_0.gguf --port 8080
```

Configure the OpenAI-compatible endpoint and launch aider:

```bash
export OPENAI_API_BASE=http://localhost:8080/v1
export OPENAI_API_KEY=swizzle-local

aider --model openai/Qwen3-0.6B-Q8_0.gguf
```

`swizzle-rt serve` also exposes Ollama-compatible routes (`/api/chat`, `/api/generate`, `/api/tags`) and includes prefix caching (`Warm Start`) and self-speculative decoding (`RAD-1`) for multi-turn code editing sessions.
