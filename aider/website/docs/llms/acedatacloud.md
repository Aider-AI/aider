---
parent: Connecting to LLMs
nav_order: 510
description: Use Ace Data Cloud coding models with a dedicated API key.
---

# Ace Data Cloud

Ace Data Cloud provides API access to coding models. Select its named provider
with `acedatacloud/<model>`; aider sets the API endpoint automatically and reads
only `ACEDATACLOUD_API_KEY` for this provider. It does not change your OpenAI or
OpenRouter credentials.

## Install aider and get an API key

{% include install.md %}

1. [Register or sign in to Ace Data Cloud](https://platform.acedata.cloud/console/applications?utm_source=opensource&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_docs_signup).
2. Open **Applications → General application**. If it does not exist, initialize
   the General application first. Copy its API token or open **Manage Keys** to
   create a dedicated token named `Aider`.
3. Check your account's model access, token expiration, allowed APIs, balance and
   [current prices](https://platform.acedata.cloud/models?utm_source=opensource&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_docs_pricing).
   A restricted token must allow Chat Completions for the selected model.

![Copy a token or open Manage Keys; credentials are redacted](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/get-api-key-en.png)

![Create an optional dedicated API token](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/create-api-key-en.png)

These are Ace Data Cloud's Applications/Key screenshots (source commit dated
2026-10-08), published in its
Suno integration guide and reused for the shared key workflow. They are not
aider settings or evidence of a model request. The name `Dify tutorial` in the
original screenshot is an example; use `Aider` for your dedicated token. Choose Chat Completions access
for aider, not the Suno generation/task APIs used in the original tutorial.

Use the API token string, without `Bearer ` or quotation marks. A platform
management token is not the model API key. Do not commit credentials to a repo.

## Select Ace Data Cloud

Set the key in the shell that launches aider:

```bash
# macOS / Linux: load ACEDATACLOUD_API_KEY from your secret manager.
export ACEDATACLOUD_API_KEY

# Select a model your account can use.
aider --model acedatacloud/gpt-4.1

# Find the bundled Ace Data Cloud model preset.
aider --list-models acedatacloud/
```

On Windows, set `ACEDATACLOUD_API_KEY` in your environment and restart the shell.
Do not put a real token in a shared command or screenshot. Use a different exact
model ID after the prefix if your account has access to it. A provider key alone
does not choose or silently substitute a paid model.

The preset uses `https://api.acedata.cloud/v1` with Chat Completions. You do not
need `OPENAI_API_BASE`, `OPENAI_API_KEY` or an extra config file. The existing
[OpenAI-compatible configuration](openai-compat.html) remains available on older
aider releases that do not include this provider.

## Check a small coding task

In a scratch directory, add one file to the chat and ask for a small edit. Check
the actual file and run its tests; a text answer alone does not prove an edit was
applied. [Linting and testing](../usage/lint-test.html) can feed failed tests back
into the next model turn. Those turns also use tokens.

This is a coding-model connection. Suno, Seedance, HappyHorse, GPT Image and Nano
Banana media-generation tasks are not aider model presets or installable tools.
Use a client with the relevant service integration for those workflows.

## Troubleshooting

- Missing key: this provider requires `ACEDATACLOUD_API_KEY`, even if an OpenAI
  key is set. Check the environment of the process that runs aider.
- Unknown model metadata: account prices and model limits may differ from the
  model vendor's. This integration does not copy another provider's prices or
  context limits. Check the actual Ace Data Cloud usage and billing records.
- 401/403: check token validity, expiry and API/model access; preserve the server
  error details and never share your token.
- 404: check the exact model ID. The provider sets its own base URL.
- 429 or service errors: stop and inspect request history before retrying;
  do not repeatedly submit paid requests or automatically switch models.

[API key management](https://platform.acedata.cloud/console/applications?utm_source=opensource&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_docs_api_key)
and [Ace Data Cloud's aider guide](https://platform.acedata.cloud/documents/aider-cli-integration?utm_source=opensource&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_docs_setup)
provide account-specific setup details.
