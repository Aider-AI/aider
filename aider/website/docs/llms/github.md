---
parent: Connecting to LLMs
nav_order: 510
---

# GitHub Copilot models

Aider can talk to the GitHub Copilot LLMs because Copilot exposes an **OpenAI-compatible** REST
API at `https://api.githubcopilot.com`.

The only trick is getting an OAuth access token that has permission to call the Copilot
endpoint.  
The easiest, **official** way is to sign in to Copilot from any JetBrains IDE
(Goland, PyCharm, etc).  
After you sign in, a file appears at:

```
~/.config/github-copilot/apps.json
```

Inside you will find an `oauth_token` value – copy that string, **it is your API key**.

---

## Configure the environment

```bash
# macOS/Linux
export OPENAI_API_BASE=https://api.githubcopilot.com
export OPENAI_API_KEY=<oauth_token from apps.json>

# Windows (PowerShell)
setx OPENAI_API_BASE https://api.githubcopilot.com
setx OPENAI_API_KEY  <oauth_token>
# …restart the shell so the variables are picked up
```

---

## Pick a model

Copilot hosts many models (OpenAI, Anthropic, Google, etc).  
You can discover the list that your subscription allows with:

```bash
curl -s https://api.githubcopilot.com/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Copilot-Integration-Id: vscode-chat" | jq -r '.data[].id'
```

The returned IDs are used exactly like OpenAI models, but **prefixed with `openai/`** when you
pass them to aider:

```bash
aider --model openai/gpt-4o
# or
aider --model openai/claude-3.7-sonnet-thought
```

You can also store this in `~/.aider.conf.yml`:

```yaml
openai-api-base: https://api.githubcopilot.com
openai-api-key:  "<oauth_token>"
model:           openai/gpt-4o
weak-model:      openai/gpt-4o-mini
show-model-warnings: false
```

---

## Notes & FAQ

* Copilot billing is handled entirely by GitHub.  Calls made through aider count against your
  Copilot subscription, even though aider will still print estimated costs.
* Tokens created by **Neovim copilot.lua** or older `hosts.json` files sometimes lack the
  required scopes. If you get `access to this endpoint is forbidden`, regenerate the token via a
  JetBrains IDE or VS Code Copilot extension.
* The Copilot terms of service allow third-party “agents” that access the LLM endpoint.  Aider
  merely follows the documented API and **does not scrape the web UI**.

