# Ollama Cloud Models Integration

This document describes the custom Ollama cloud models that have been integrated into Aider.

## Available Models

The following Ollama cloud models are now available in Aider:

### 1. **Kimi K2 (1T parameters)**
- **Full name**: `ollama_chat/kimi-k2:1t-cloud` or `ollama/kimi-k2:1t-cloud`
- **Alias**: `kimi-cloud`
- **Provider**: Moonshot AI
- **Context window**: 128K tokens
- **Configuration**:
  - Edit format: diff
  - Repository map: enabled
  - Temperature: 0.6
  - Best for: General coding tasks and conversations

### 2. **DeepSeek v3.1 (671B parameters)**
- **Full name**: `ollama_chat/deepseek-v3.1:671b-cloud` or `ollama/deepseek-v3.1:671b-cloud`
- **Alias**: `deepseek-cloud`
- **Provider**: DeepSeek
- **Context window**: 128K tokens
- **Configuration**:
  - Edit format: diff
  - Repository map: enabled
  - Max tokens: 8192
  - Best for: Complex code generation and refactoring

### 3. **Qwen3 Coder (480B parameters)**
- **Full name**: `ollama_chat/qwen3-coder:480b-cloud` or `ollama/qwen3-coder:480b-cloud`
- **Alias**: `qwen-coder-cloud`
- **Provider**: Alibaba Cloud (Qwen)
- **Context window**: 128K tokens
- **Configuration**:
  - Edit format: diff
  - Repository map: enabled
  - Editor edit format: editor-diff
  - Best for: Code-focused tasks and programming

### 4. **GPT-OSS (120B parameters)**
- **Full name**: `ollama_chat/gpt-oss:120b-cloud` or `ollama/gpt-oss:120b-cloud`
- **Alias**: `gpt-oss-cloud`
- **Context window**: 128K tokens
- **Configuration**:
  - Edit format: diff
  - Repository map: enabled
  - Best for: General purpose coding and documentation

### 5. **Qwen3 VL (235B parameters)**
- **Full name**: `ollama_chat/qwen3-vl:235b-cloud` or `ollama/qwen3-vl:235b-cloud`
- **Alias**: `qwen-vl-cloud`
- **Provider**: Alibaba Cloud (Qwen)
- **Type**: Vision-Language Model
- **Context window**: 128K tokens
- **Configuration**:
  - Edit format: diff
  - Repository map: enabled
  - Temperature: 0.7
  - System prompt prefix: "/no_think"
  - Advanced parameters: top_p=0.8, top_k=20, min_p=0.0
  - Best for: Code generation with vision capabilities

## Usage

### Basic Usage

You can use any of these models in three ways:

#### 1. Using the full model name:
```bash
aider --model ollama_chat/kimi-k2:1t-cloud
```

#### 2. Using the short alias:
```bash
aider --model kimi-cloud
```

#### 3. Using the ollama/ prefix:
```bash
aider --model ollama/deepseek-v3.1:671b-cloud
```

### Configuration

#### Environment Variables

If your Ollama instance requires authentication:
```bash
export OLLAMA_API_KEY=<your-api-key>
export OLLAMA_API_BASE=http://127.0.0.1:11434  # or your cloud endpoint
```

#### Model-Specific Settings

You can override model settings in your `.aider.model.settings.yml` file:

```yaml
- name: ollama_chat/kimi-k2:1t-cloud
  extra_params:
    num_ctx: 256000  # Increase context window
    temperature: 0.8  # Adjust temperature
```

## Features

All cloud models include:
- ✅ **Large context windows** (128K tokens)
- ✅ **Repository mapping** for better code understanding
- ✅ **Diff-based editing** for precise code changes
- ✅ **Optimized parameters** for each model's strengths

## Performance Tips

1. **Kimi K2**: Great for multi-turn conversations and understanding large codebases
2. **DeepSeek v3.1**: Excellent for complex refactoring and algorithmic tasks
3. **Qwen3 Coder**: Specialized for code generation and optimization
4. **GPT-OSS**: Balanced general-purpose model
5. **Qwen3 VL**: Can process both code and visual inputs (diagrams, screenshots)

## Troubleshooting

### Model not found
Make sure the model is available in your Ollama instance:
```bash
ollama list
```

### Connection issues
Verify your `OLLAMA_API_BASE` is set correctly:
```bash
echo $OLLAMA_API_BASE
```

### Performance issues
Try reducing the context window in your model settings if experiencing slowness:
```yaml
- name: ollama_chat/your-model
  extra_params:
    num_ctx: 32768  # Smaller context window
```

## Examples

### Using Kimi K2 for a new feature:
```bash
aider --model kimi-cloud --message "Add user authentication to the API"
```

### Using DeepSeek v3.1 for refactoring:
```bash
aider --model deepseek-cloud --message "Refactor the database layer to use async/await"
```

### Using Qwen3 Coder for code review:
```bash
aider --model qwen-coder-cloud --message "Review this code for best practices"
```

## Additional Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [Aider Documentation](https://aider.chat/docs)
- [Model Settings Reference](https://aider.chat/docs/config/adv-model-settings.html)
