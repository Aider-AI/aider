---
parent: Connecting to LLMs
nav_order: 520
---

# NetMind

Aider can use models hosted by [NetMind](https://www.netmind.ai/) through its
OpenAI-compatible API.

First, install aider:

{% include install.md %}

Then configure the NetMind endpoint and API key:

```bash
# macOS/Linux
export NETMIND_API_KEY=<your-netmind-api-key>
export OPENAI_API_BASE=https://api.netmind.ai/inference-api/v1
export OPENAI_API_KEY="$NETMIND_API_KEY"
```

On Windows PowerShell:

```powershell
setx OPENAI_API_BASE "https://api.netmind.ai/inference-api/v1"
setx OPENAI_API_KEY "<your-netmind-api-key>"
# Restart PowerShell after running setx.
```

The bundled metadata covers all 31 models in NetMind's current catalog. The commands
below use `Qwen/Qwen3.8-Flash` as an example; you can replace it with any supported
NetMind model ID.

Start aider with the fully qualified NetMind model ID:

```bash
cd /path/to/your/project
aider --model openai/Qwen/Qwen3.8-Flash
```

The `openai/` prefix selects LiteLLM's OpenAI-compatible request path. The
model ID sent to NetMind remains `Qwen/Qwen3.8-Flash`.

## Optional config file

You can save the endpoint and model in `~/.aider.conf.yml`:

```yaml
model: openai/Qwen/Qwen3.8-Flash
set-env:
  - OPENAI_API_BASE=https://api.netmind.ai/inference-api/v1
```

Keep the API key in the environment rather than storing it in the config file.

## Model support

The configured model supports streaming and Aider's code-editing workflow. Its
metadata declares a 1,000,000-token context window, up to 131,072 output tokens,
and function calling support. Pricing is intentionally omitted because Aider
does not require it for model operation and NetMind pricing may change.

NetMind's OpenAI-compatible `/models` endpoint does not currently provide model
discovery, so enter the exact model ID manually. Image input has not been
verified for this model.

If authentication fails, verify that `OPENAI_API_KEY` is available in the same
shell that starts aider. If requests cannot connect, verify that
`OPENAI_API_BASE` includes `/inference-api/v1`.
