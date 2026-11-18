"""Make stored browser sign-ins work for model calls (the FineCode / Pi model).

Anthropic (Claude Pro/Max)
    litellm already sends a `sk-ant-oat...` token as a Bearer token with the OAuth beta.
    FineCode also sends the Claude Code identity, which Anthropic requires for OAuth tokens:
    a system block "You are Claude Code, ...", the `claude-code` beta, and the claude-cli
    User-Agent. These are added here, for OAuth tokens only.

OpenAI (ChatGPT Plus/Pro)
    litellm's `chatgpt/` provider ignores the key it is given. It reads an auth file from
    CHATGPT_TOKEN_DIR, refreshes the token itself, and starts a device-code login when no
    valid token is there. So, before each call, this module writes that file from the
    credential store (after renewing it, so litellm does not need to refresh). After the
    call it copies back any token litellm rotated, so the stored refresh token is not lost.

No network access happens here except through the stores and litellm.
"""

import json
import os
import time
from pathlib import Path

from aider import auth

ANTHROPIC_OAUTH_PREFIX = "sk-ant-oat"
CLAUDE_CODE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
CLAUDE_CODE_BETA = "claude-code-20250219"
CLAUDE_CODE_VERSION = "2.1.280"
CHATGPT_MODEL_PREFIX = "chatgpt/"
CHATGPT_TOKEN_DIR = Path.home() / ".aider" / "chatgpt"
CHATGPT_AUTH_FILE = "auth.json"


def is_anthropic_oauth_call(model_name, environ):
    """True when this call goes to Anthropic with a subscription token."""
    key = environ.get("ANTHROPIC_API_KEY") or ""
    if not key.startswith(ANTHROPIC_OAUTH_PREFIX):
        return False
    name = (model_name or "").lower()
    return name.startswith("anthropic/") or name.startswith("claude")


def anthropic_oauth_adjustments(messages, extra_headers):
    """Return (messages, extra_headers) with the Claude Code identity for an OAuth token."""
    headers = dict(extra_headers or {})
    betas = [b.strip() for b in headers.get("anthropic-beta", "").split(",") if b.strip()]
    if CLAUDE_CODE_BETA not in betas:
        betas.append(CLAUDE_CODE_BETA)
    headers["anthropic-beta"] = ",".join(betas)
    headers["user-agent"] = f"claude-cli/{CLAUDE_CODE_VERSION}"
    headers["x-app"] = "cli"
    identity = {"role": "system", "content": CLAUDE_CODE_IDENTITY}
    return [identity] + list(messages), headers


def is_chatgpt_call(model_name):
    return (model_name or "").startswith(CHATGPT_MODEL_PREFIX)


def chatgpt_completion_model(model_name):
    """chatgpt/<model> -> chatgpt/responses/<model>.

    The ChatGPT backend only speaks the Responses API. litellm bridges completion()
    to it only for the `responses/` form, which sends the account header and the
    Codex originator.
    """
    if "/responses/" in model_name:
        return model_name
    return model_name.replace(CHATGPT_MODEL_PREFIX, CHATGPT_MODEL_PREFIX + "responses/", 1)


def token_dir(environ):
    return Path(environ.get("AIDER_CHATGPT_TOKEN_DIR") or CHATGPT_TOKEN_DIR)


def prepare_chatgpt_auth(store, environ):
    """Write the litellm auth file from the stored ChatGPT sign-in.

    Raises AuthError when there is no browser sign-in, instead of letting litellm
    start a device-code login inside aider.
    """
    stored = store.read("openai")
    if not stored or stored.get("type") != "oauth" or not stored.get("accountId"):
        raise auth.AuthError(
            "The chatgpt/ models need a ChatGPT sign-in. Run `aider --login openai` first."
        )
    auth.resolve("openai", store, environ)  # renews the token when it is close to expiry
    stored = store.read("openai")
    directory = token_dir(environ)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "access_token": stored["access"],
        "refresh_token": stored["refresh"],
        "id_token": None,
        "expires_at": int(stored["expires"] / 1000),
        "account_id": stored["accountId"],
    }
    path = directory / CHATGPT_AUTH_FILE
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    environ["CHATGPT_TOKEN_DIR"] = str(directory)
    return path


def sync_chatgpt_auth(store, environ):
    """Copy a token that litellm rotated back into the credential store."""
    path = token_dir(environ) / CHATGPT_AUTH_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    stored = store.read("openai")
    if not stored or stored.get("type") != "oauth" or not isinstance(data, dict):
        return False
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    if not access or not refresh or access == stored.get("access"):
        return False
    expires_at = data.get("expires_at")
    expires = int(expires_at * 1000) if isinstance(expires_at, (int, float)) else None
    if expires is None:
        expires = int(time.time() * 1000) + 3600 * 1000
    updated = {
        "type": "oauth",
        "access": access,
        "refresh": refresh,
        "expires": expires,
        "accountId": data.get("account_id") or stored.get("accountId"),
    }
    store.modify("openai", lambda current: updated)
    return True
