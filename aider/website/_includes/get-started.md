
If you already have python 3.8-3.13 installed, you can get started quickly like this.

First, install aider:

{% include install.md %}

Start working with aider on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# DeepSeek
aider --model deepseek --api-key deepseek=<key>

# Claude 3.7 Sonnet
aider --model sonnet --api-key anthropic=<key>

# o3-mini
aider --model o3-mini --api-key openai=<key>
```
