---
parent: Configuration
nav_order: 5
description: Setting API keys for API providers.
---

# API Keys

Aider lets you specify API keys in a few ways:

- On the command line
- As environment variables
- In a `.env` file
- In your `.aider.conf.yml` config file

---

## OpenAI and Anthropic

Aider has special support for providing
OpenAI and Anthropic API keys
via dedicated switches and configuration options.
Settings keys for other providers works a bit differently, see below.

#### Command line

You can set OpenAI and Anthropic API keys via
[command line switches](/docs/config/options.html#api-keys-and-settings)
`--openai-api-key` and `--anthropic-api-key`.


#### Environment variables or .env file

You can also store them in environment variables or a 
[.env file](/docs/config/dotenv.html), which also works
for every API provider:

```
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
```

#### Yaml config file
You can also set those API keys via special entries in the
[yaml config file](/docs/config/aider_conf.html), like this:

```yaml
openai-api-key: <key>
anthropic-api-key: <key>
```


---

## Other API providers

All other LLM providers can use one of these other methods to set their API keys.

#### Command line
{: .no_toc }

Use `--api-key provider=<key>` which has the effect of setting the environment variable `PROVIDER_API_KEY=<key>`. So `--api-key gemini=xxx` would set `GEMINI_API_KEY=xxx`.

#### Environment variables or .env file
{: .no_toc }

You can set API keys in environment variables.
The [.env file](/docs/config/dotenv.html)
is a great place to store your API keys and other provider API environment variables:

```bash
GEMINI_API_KEY=foo
OPENROUTER_API_KEY=bar
DEEPSEEK_API_KEY=baz
```

#### Yaml config file


You can also set API keys in the 
[`.aider.conf.yml` file](/docs/config/aider_conf.html)
via the `api-key` entry:

```
api-key:
- gemini=foo      # Sets env var GEMINI_API_KEY=foo
- openrouter=bar  # Sets env var OPENROUTER_API_KEY=bar
- deepseek=baz    # Sets env var DEEPSEEK_API_KEY=baz
```

