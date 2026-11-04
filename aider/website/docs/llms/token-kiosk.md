---
parent: Connecting to LLMs
nav_order: 750
---

# Token Kiosk

Aider can connect to frontier and open-source models through [Token Kiosk](https://token-kiosk.gaib.ai), GAIB's multi-provider AI model routing gateway (`https://agent-router.gaib.ai/v1`).

First, install aider:

{% include install.md %}

Then configure your Token Kiosk API key and endpoint:

```bash
# Mac/Linux:
export OPENAI_API_BASE=https://agent-router.gaib.ai/v1
export OPENAI_API_KEY=<your-token-kiosk-api-key>

# Windows:
setx OPENAI_API_BASE https://agent-router.gaib.ai/v1
setx OPENAI_API_KEY <your-token-kiosk-api-key>
# ... restart shell after setx commands
```

Start working with aider and Token Kiosk on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Route through Token Kiosk (e.g. Claude 3.5 Sonnet, GPT-4o, DeepSeek-R1)
aider --model openai/claude-3-5-sonnet
```
