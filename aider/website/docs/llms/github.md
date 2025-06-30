---
parent: Connecting to LLMs
nav_order: 510
---

# GitHub

Aider can connect to both GitHub Models and GitHub Copilot, which are different GitHub services
that expose **OpenAI-style** endpoints.

---

## GitHub Models

GitHub Models provides access to AI models through a simple API using your GitHub Personal Access Token.
GitHub Models uses the endpoint:

```
https://models.github.ai/inference
```

First, install aider:

{% include install.md %}

### Configure your environment

You can set up GitHub Models in two ways:

**Option 1: Using --api-key (recommended)**
```bash
aider --api-key github=<your_github_pat> --model github/gpt-4.1
```

**Option 2: Using environment variables**
```bash
# macOS/Linux
export GITHUB_API_KEY=<your_github_pat>

# Windows (PowerShell)
setx GITHUB_API_KEY <your_github_pat>
# …restart the shell after setx commands
```

When you set `GITHUB_API_KEY`, aider automatically configures the GitHub Models endpoint.

### Where do I get the GitHub Personal Access Token?

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)" or "Fine-grained personal access token"
3. For classic tokens: Select the `models:read` scope
4. For fine-grained tokens: Grant "Models" repository permissions
5. Copy the generated token

### Available models

GitHub Models provides access to various AI models with their publisher prefixes:

```bash
# OpenAI models
aider --model github/gpt-4.1
aider --model github/deepseek-r1
aider --model github/codestral-2501
aider --model github/phi-4-mini-reasoning
```

### Quick start

```bash
# Using --api-key
aider --api-key github=ghp_your_token_here --model github/gpt-4.1

# Or with environment variable
export GITHUB_API_KEY=ghp_your_token_here
aider --model github/gpt-4.1
```

### Optional config file (`~/.aider.conf.yml`)

```yaml
api-key:
  - github=<your_github_pat>
model: github/gpt-4.1
weak-model: github/gpt-4.1-mini
```

---

## GitHub Copilot

Aider can connect to GitHub Copilot's LLMs because Copilot exposes a standard **OpenAI-style**
endpoint at:

```
https://api.githubcopilot.com
```

### Configure your environment

```bash
# macOS/Linux
export OPENAI_API_BASE=https://api.githubcopilot.com
export OPENAI_API_KEY=<oauth_token>

# Windows (PowerShell)
setx OPENAI_API_BASE https://api.githubcopilot.com
setx OPENAI_API_KEY  <oauth_token>
# …restart the shell after setx commands
```

### Where do I get the token?
The easiest path is to sign in to Copilot from any JetBrains IDE (PyCharm, GoLand, etc).
After you authenticate a file appears:

```
~/.config/github-copilot/apps.json
```

On Windows the config can be found in:

```
~\AppData\Local\github-copilot\apps.json
```

Copy the `oauth_token` value – that string is your `OPENAI_API_KEY`.

*Note:* tokens created by the Neovim **copilot.lua** plugin (old `hosts.json`) sometimes lack the
needed scopes. If you see "access to this endpoint is forbidden", regenerate the token with a
JetBrains IDE.

### Discover available models

Copilot hosts many models (OpenAI, Anthropic, Google, etc).  
List the models your subscription allows with:

```bash
curl -s https://api.githubcopilot.com/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Copilot-Integration-Id: vscode-chat" | jq -r '.data[].id'
```

Each returned ID can be used with aider by **prefixing it with `openai/`**:

```bash
aider --model openai/gpt-4o
# or
aider --model openai/claude-3.7-sonnet-thought
```

### Quick start

```bash
# change into your project
cd /to/your/project

# talk to Copilot
aider --model openai/gpt-4o
```

### Optional config file (`~/.aider.conf.yml`)

```yaml
openai-api-base: https://api.githubcopilot.com
openai-api-key:  "<oauth_token>"
model:           openai/gpt-4o
weak-model:      openai/gpt-4o-mini
show-model-warnings: false
```

---

## FAQ

### GitHub Models
* GitHub Models provides free tier access to various AI models, plus an optional paid tier for higher rate limits
* Models are referenced with their publisher prefix (e.g., `openai/gpt-4o`)
* Requires a GitHub Personal Access Token with `models:read` permission

### GitHub Copilot
* Calls made through aider are billed through your Copilot subscription  
  (aider will still print *estimated* costs).
* The Copilot docs explicitly allow third-party “agents” that hit this API – aider is playing by
  the rules.
* Aider talks directly to the REST endpoint—no web-UI scraping or browser automation.

