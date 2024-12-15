---
parent: Configuration
nav_order: 5
description: Setting API keys for API providers.
---

# API Keys

### OpenAI and Anthropic

Aider has special support for providing
OpenAI and Anthropic API keys
via dedicated switches and configuration options.
Settings keys for other providers works a bit differently, see below.

You can set OpenAI and Anthropic API keys via
[command line switches](/docs/config/options.html#api-keys-and-settings)
`--openai-api-key` and `--anthropic-api-key`.

You can also set those API keys via special entries in the
[yaml config file](/docs/config/aider_conf.html), like this:

```yaml
openai-api-key: <key>
anthropic-api-key: <key>
```

You can also store them in environment variables or a 
[.env file](/docs/config/dotenv.html), which also works
for every API provider:

```
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
```

All other LLM providers can use one of these other methods to set their API keys.

### API keys on the command line
{: .no_toc }

Use `--api-key provider=<key>` which has the effect of setting the environment variable `PROVIDER_API_KEY=<key>`. So `--api-key gemini=xxx` would set `GEMINI_API_KEY=xxx`.

### API keys in .aider.conf.yml
{: .no_toc }

You can also set API keys in the 
[`.aider.conf.yml` file](/docs/config/aider_conf.html)
via the `api-key` entry:

```
api-key:
- gemini=foo      # Sets env var GEMINI_API_KEY=foo
- openrouter=bar  # Sets env var OPENROUTER_API_KEY=bar
- deepseek=baz    # Sets env var DEEPSEEK_API_KEY=baz
```

### API keys in a .env file
{: .no_toc }

The [.env file](/docs/config/dotenv.html)
is a great place to set API keys and other provider API environment variables:

```bash
GEMINI_API_KEY=foo
OPENROUTER_API_KEY=bar
DEEPSEEK_API_KEY=baz
```
