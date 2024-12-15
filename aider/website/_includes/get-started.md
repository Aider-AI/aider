
You can get started quickly like this, with python 3.8-3.13:

```bash
python -m pip install aider-install
aider-install

# Change directory into your code base
cd /to/your/git/repo

# Work with Claude 3.5 Sonnet on your repo
aider --model sonnet --anthropic-api-key your-key-goes-here

# Work with GPT-4o on your repo
aider --model gpt-4o --openai-api-key your-key-goes-here
```
