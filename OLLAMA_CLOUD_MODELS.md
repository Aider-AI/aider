# Ollama Cloud Models Integration

This Aider fork includes support for **5 powerful Ollama cloud models** optimized for AI-assisted development.

---

## 📦 Available Models

### 1. **Kimi K2** (1T parameters)
- **Full name**: `ollama_chat/kimi-k2:1t-cloud`
- **Alias**: `kimi-cloud`
- **Provider**: Moonshot AI
- **Context**: 128K tokens
- **Best for**: General coding and conversations

### 2. **DeepSeek v3.1** (671B parameters)
- **Full name**: `ollama_chat/deepseek-v3.1:671b-cloud`
- **Alias**: `deepseek-cloud`
- **Provider**: DeepSeek
- **Context**: 128K tokens
- **Best for**: Complex code generation and refactoring

### 3. **Qwen3 Coder** (480B parameters)
- **Full name**: `ollama_chat/qwen3-coder:480b-cloud`
- **Alias**: `qwen-coder-cloud`
- **Provider**: Alibaba (Qwen)
- **Context**: 128K tokens
- **Best for**: Code-focused tasks

### 4. **GPT-OSS** (120B parameters)
- **Full name**: `ollama_chat/gpt-oss:120b-cloud`
- **Alias**: `gpt-oss-cloud`
- **Context**: 128K tokens
- **Best for**: General purpose coding

### 5. **Qwen3 VL** (235B parameters)
- **Full name**: `ollama_chat/qwen3-vl:235b-cloud`
- **Alias**: `qwen-vl-cloud`
- **Provider**: Alibaba (Qwen)
- **Type**: Vision-Language Model
- **Context**: 128K tokens
- **Best for**: Code with vision capabilities

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Thundernight1/ThunderNight-aider.git
cd ThunderNight-aider

# 2. Install
pip install -e .

# 3. Configure Ollama API
export OLLAMA_API_BASE=http://127.0.0.1:11434
export OLLAMA_API_KEY="your-key-if-needed"
