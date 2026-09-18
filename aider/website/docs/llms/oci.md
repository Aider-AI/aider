---
parent: Connecting to LLMs
nav_order: 570
---

# OCI Generative AI

Aider can connect to models hosted by
[Oracle Cloud Infrastructure (OCI) Generative AI](https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm),
such as Meta Llama, xAI Grok, Cohere Command, Google Gemini and OpenAI gpt-oss.

There are two ways to connect:

- The `oci/` provider, which signs each request with an
  [OCI API signing key](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm).
- OCI's [OpenAI-compatible endpoint](https://docs.oracle.com/en-us/iaas/Content/generative-ai/openai-compatible-api.htm),
  which authenticates with an
  [OCI Generative AI API key](https://docs.oracle.com/en-us/iaas/Content/generative-ai/api-keys.htm).

First, install aider:

{% include install.md %}

## Option 1: OCI API signing key

You need an OCI user with an
[API signing key](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm)
and an [IAM policy](https://docs.oracle.com/en-us/iaas/Content/generative-ai/iam-policies.htm)
that lets the user's group call the service, for example:

```
allow group <your-group-name> to use generative-ai-family in compartment <your-compartment-name>
```

### Install cryptography

The `oci/` provider needs the `cryptography` package to sign requests.
It is not installed with aider by default.

```bash
# If you installed with aider-install or `uv tool`
uv tool install --force --python python3.12 --with cryptography aider-chat

# Or with pipx...
pipx inject aider-chat cryptography

# Or with pip
pip install -U cryptography
```

### Configure credentials

The version of litellm that ships with aider does not read `OCI_*` environment variables,
so pass the credentials as litellm parameters with a
[model settings file](/docs/config/adv-model-settings.html).
Put the file at `~/.aider.model.settings.yml` in your home directory,
so the values are not committed with your code:

```yaml
- name: oci/meta.llama-3.3-70b-instruct
  extra_params:
    oci_region: us-chicago-1
    oci_user: ocid1.user.oc1..YOUR_USER_OCID
    oci_fingerprint: aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
    oci_tenancy: ocid1.tenancy.oc1..YOUR_TENANCY_OCID
    oci_key_file: /path/to/oci_api_key.pem  # absolute path
    oci_compartment_id: ocid1.compartment.oc1..YOUR_COMPARTMENT_OCID
```

These are the same values as in your `~/.oci/config` profile.
`oci_region` defaults to `us-ashburn-1` if omitted.
To use the same credentials for every model, put the `extra_params`
under the special name `aider/extra_params` instead of repeating them per model.

### Get started

```bash
# Change directory into your codebase
cd /to/your/project

aider --model oci/meta.llama-3.3-70b-instruct

# List models available from OCI
aider --list-models oci/
```

The `aider --list-models oci/` command lists the OCI models that aider knows about,
not the models enabled in your tenancy.
Any model from the
[OCI pretrained models list](https://docs.oracle.com/en-us/iaas/Content/generative-ai/pretrained-models.htm)
can be used as `oci/<model-id>`, for example `oci/xai.grok-4.6` or `oci/openai.gpt-oss-120b`.
See the [model warnings](warnings.html) section for information on warnings
which will occur when working with models that aider is not familiar with.

## Option 2: OpenAI-compatible endpoint

OCI Generative AI also provides an OpenAI-compatible endpoint
that authenticates with a Bearer API key,
so no signing key or extra package is needed.

First add an
[IAM policy](https://docs.oracle.com/en-us/iaas/Content/generative-ai/add-api-permission.htm)
that authorizes API keys in the compartment, *then*
[create the API key](https://docs.oracle.com/en-us/iaas/Content/generative-ai/create-api-key.htm):

```
allow any-user to use generative-ai-family in compartment <your-compartment-name> where ALL {request.principal.type='generativeaiapikey'}
```

The order matters: a key created before the policy exists keeps returning `401` errors
even after the policy is added. If that happens, create a new key.

Then configure aider like any other [OpenAI compatible API](openai-compat.html),
using your region in the endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://inference.generativeai.<region>.oci.oraclecloud.com/openai/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://inference.generativeai.<region>.oci.oraclecloud.com/openai/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and OCI on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the OCI model id with openai/
aider --model openai/xai.grok-4.6
```

This endpoint serves the Meta Llama, xAI Grok and OpenAI gpt-oss models,
for example `openai/meta.llama-3.3-70b-instruct` or `openai/openai.gpt-oss-120b`.

# More info

See the [litellm docs on OCI](https://docs.litellm.ai/docs/providers/oci).
