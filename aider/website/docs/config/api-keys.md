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

## Sign in from the command line

`aider --login` stores a credential so you do not need to set an environment variable.

```bash
aider --login                          # choose a provider, then a method
aider --login openrouter               # browser sign-in (default for OpenRouter)
aider --login openai --method key      # paste an API key (input is hidden)
aider --logout openrouter              # remove the stored credential
```

- Browser sign-in is available for OpenRouter. It opens your browser on the
  provider's sign-in page, and aider waits for the callback on `127.0.0.1`.
- If no callback arrives within 60 seconds, aider asks you to paste the redirect
  URL from the browser's address bar. Pressing Enter keeps waiting. The sign-in
  times out after 5 minutes.
- On an SSH session or a Linux machine with no display, aider skips the browser
  and asks for the code shown on the provider's page.
- Credentials are stored in `~/.aider/auth.json`, with file mode `0600`. Each
  provider has one entry.

**Precedence.** A stored credential wins over environment variables and `.env`
files. Environment variables are used only when nothing is stored for that
provider. An explicit `--api-key` flag still wins over both.

**Removing a credential.** `aider --logout PROVIDER` removes only the stored
entry. Environment variables and `.env` files are not changed.

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

#### YAML config file
You can also set those API keys via special entries in the
[YAML config file](/docs/config/aider_conf.html), like this:

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

#### YAML config file


You can also set API keys in the 
[`.aider.conf.yml` file](/docs/config/aider_conf.html)
via the `api-key` entry:

```
api-key:
- gemini=foo      # Sets env var GEMINI_API_KEY=foo
- openrouter=bar  # Sets env var OPENROUTER_API_KEY=bar
- deepseek=baz    # Sets env var DEEPSEEK_API_KEY=baz
```

