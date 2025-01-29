
If you already have python 3.8-3.13 installed, you can get started quickly like this:

```bash
python -m pip install aider-install
aider-install

# Change directory into your code base
cd /to/your/project

# Work with DeepSeek on your code
aider --model deepseek --api-key deepseek=your-key-goes-here

# Work with Claude 3.5 Sonnet on your code
aider --model sonnet --api-key anthropic=your-key-goes-here

# Work with GPT-4o on your code
aider --model gpt-4o --api-key openai=your-key-goes-here
```
