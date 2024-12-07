
Aider has special support for providing
OpenAI and Anthropic API keys
via dedicated
[command line switches](/docs/config/options.html#api-keys-and-settings)
`--openai-api-key` and `--anthropic-api-key`.

You can also set those API keys via special entries in the
[yaml config file](/docs/config/aider_conf.html), like this:

```yaml
openai-api-key: <key>
anthropic-api-key: <key>
```

All other LLM providers can use one of the following methods to set their
keys:

### API keys on the command line
{: .no_toc }

Use `--api-key provider=<key>` which has the effect of setting the environment variable `PROVIDER_API_KEY=<key>`. So `--api-key gemini=xxx` would set `GEMINI_API_KEY=xxx`.

### API keys in a .env file
{: .no_toc }

The [.env file](/docs/config/dotenv.html)
is a great place to set API keys and other provider API environment variables:

```bash
GEMINI_API_KEY=foo
OPENROUTER_API_KEY=bar
DEEPSEEK_API_KEY=baz
```

### API keys in .aider.conf.yml
{: .no_toc }

Or you can set API keys in the 
[`.aider.conf.yml` file](/docs/config/aider_conf.html)
via the `api-key` entry:

```
api-key:
- gemini=foo      # Sets env var GEMINI_API_KEY=foo
- openrouter=bar  # Sets env var OPENROUTER_API_KEY=bar
- deepseek=baz    # Sets env var DEEPSEEK_API_KEY=baz
```

