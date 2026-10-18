# Ace Data Cloud integration for Aider

This is the Ace Data Cloud maintained **candidate** for Aider's named coding-model provider, based on upstream commit `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`. It is not an official Aider release, marketplace plugin, or an endorsement by Aider AI.

**Source review:** see the pull request in this repository. The official upstream currently has no Ace Data Cloud preset. After upstream review and a release containing it, the intended user flow is `aider --model acedatacloud/<model>` with a dedicated `ACEDATACLOUD_API_KEY`, without a separate base URL.

## Install and choose the correct version

Start with [Aider's official installation instructions](https://aider.chat/docs/install.html). Current stable `aider-chat==0.86.2` does **not** include this candidate. Use the existing [manual Ace setup](https://platform.acedata.cloud/documents/aider-cli-integration?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_setup) with that release; do not paste the new provider selector into an unmodified stable installation and assume it works.

For source reviewers, use a separate environment, check out this candidate branch, install its declared dependencies and run the offline tests. Keep real credentials out of source review. No official package or marketplace installation is claimed here.

## Register and create a token

1. [Register/sign in → Applications](https://platform.acedata.cloud/console/applications?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_signup).
2. Open **General application**, or initialize it if it does not exist. Copy the API token, or choose **Manage Keys → Create** for a token named `Aider`.
3. Check Chat Completions/model access, expiry, usage restrictions and balance. [Read current prices](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_pricing) before sending a coding request.

![Copy the API token or open Manage Keys; real values are redacted](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/get-api-key-en.png)

![Create a separate token](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/create-api-key-en.png)

These are original Ace Applications screenshots from source commit dated 2026-10-08, reused from SunoDify. The example name `Dify tutorial` is not a required value: use `Aider`. Restrict to the Chat Completions API used by your selected coding model, not the Suno APIs in the original tutorial. Copy only the token string; do not add `Bearer ` or use a platform management token.

## Native selector in the candidate source

Load `ACEDATACLOUD_API_KEY` from your secret manager into the shell that starts Aider, then choose an exact model your account permits:

```bash
export ACEDATACLOUD_API_KEY
aider --list-models acedatacloud/
aider --model acedatacloud/gpt-4.1
```

The candidate recognizes the provider, uses `https://api.acedata.cloud/v1`, and requires its own key even when an OpenAI or Copilot key is present. It does not replace another provider's credentials or choose a paid fallback. The key must already contain a value; `export` alone does not create one. User-provided model metadata may be loaded explicitly, but another provider's prices and context limits are not copied.

## First task and results

Add one scratch file, ask for one small change and run a fixed test. A real result means the file changed and tests passed, not just a model text response. The free validation here uses actual candidate Aider code with a local deterministic model fixture, covering nonstream whole-file and streamed diff edits, failed-test feedback and a repair turn. It is **not** a live Ace model/billing result.

Aider's current official code has no service plugin marketplace or merged MCP installation path. Suno, Seedance, HappyHorse, GPT Image and Nano Banana generation/query tasks are not coding-model presets. No `SunoAider` or other empty service package is created; reuse those services in a client that supports their existing integration. This integration does not create asynchronous media tasks.

## Troubleshooting

- Missing key: check `ACEDATACLOUD_API_KEY` in Aider's environment; other providers' keys are not reused.
- Unknown provider on stable Aider: use the existing manual setup or review the candidate source; it is not yet released upstream.
- 401/403: check token, API/model access, expiration and balance; never share the token.
- 404: check the exact model ID. The candidate sets the base URL automatically.
- 429/5xx: inspect the original request before retrying. Do not repeatedly send paid coding tasks.
- Client dependency import errors happen before API requests; reinstall the appropriate isolated environment. Preserve the error details.
- Aider's displayed cost is not the account's terminal bill; inspect actual Ace usage.

[API key management](https://platform.acedata.cloud/console/applications?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_api_key) · [中文指南](README_zh_CN.md) · [Official model-provider rules](https://github.com/Aider-AI/aider/blob/main/CONTRIBUTING.md)

## Upstream contribution gate

Aider requests a signed [Contributor License Agreement](https://aider.chat/docs/legal/contributor-agreement.html) during its PR process. The agent has not signed or accepted that agreement. Code, tests and a reviewable branch are prepared first; authorized human CLA handling and maintainer review remain separate from this Ace-owned source PR.
