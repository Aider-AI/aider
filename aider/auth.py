"""Provider authentication in the Pi pattern: API key or browser OAuth.

A provider declares the ways it can be signed in to (`api_key` and/or `oauth`).
Stored credentials own a provider: resolve() only consults the environment when
nothing is stored (decision D1). Resolved keys reach litellm through
os.environ, because that is how aider already passes keys (decision D9).

Explicit --api-key flags are applied later in main() and still win.
"""

import time
from dataclasses import dataclass, field

from aider.anthropic_login import AnthropicOAuth
from aider.openai_login import OpenAICodexOAuth
from aider.openrouter_login import LoginError, OpenRouterOAuth

RENEW_MARGIN_MS = 5 * 60 * 1000  # renew this long before expiry, so litellm never needs to
SOURCE_STORED = "stored"
SOURCE_ENV = "env"

API_KEY_PROVIDERS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


class AuthError(Exception):
    """Unknown provider or method. The message is safe to show to the user."""


@dataclass
class ProviderAuth:
    id: str
    name: str
    env_var: str
    oauth: object = None
    methods: tuple = field(default=("key",))


OAUTH_PROVIDERS = {
    "openrouter": OpenRouterOAuth,
    "anthropic": AnthropicOAuth,
    "openai": OpenAICodexOAuth,
}


def _build_providers():
    providers = {}
    for provider_id, env_var in API_KEY_PROVIDERS.items():
        oauth_class = OAUTH_PROVIDERS.get(provider_id)
        providers[provider_id] = ProviderAuth(
            id=provider_id,
            name=provider_id,
            env_var=env_var,
            oauth=oauth_class() if oauth_class else None,
            methods=("browser", "key") if oauth_class else ("key",),
        )
    return providers


PROVIDERS = _build_providers()


def get_provider(provider_id):
    try:
        return PROVIDERS[provider_id]
    except KeyError:
        raise AuthError(f"Unknown provider '{provider_id}'. Choose one of: {', '.join(PROVIDERS)}.")


@dataclass
class Resolved:
    api_key: str
    source: str


def resolve(provider_id, store, environ):
    """Return the key to use for a provider, or None.

    A stored credential wins. The environment is consulted only when nothing is
    stored (D1).
    """
    provider = get_provider(provider_id)
    stored = store.read(provider_id)
    if stored:
        if stored.get("type") == "oauth" and provider.oauth is not None:
            stored = _renewed(provider, store, stored)
            key = provider.oauth.to_auth(stored).get("apiKey")
        else:
            key = stored.get("key")
        if key:
            return Resolved(api_key=key, source=SOURCE_STORED)
    value = environ.get(provider.env_var)
    if value:
        return Resolved(api_key=value, source=SOURCE_ENV)
    return None


def _renewed(provider, store, credential):
    """Refresh an expired OAuth credential and store the new one (Pi rule).

    A credential without a refresh token (OpenRouter keys) is returned as is.
    """
    expires = credential.get("expires")
    if not credential.get("refresh") or not isinstance(expires, (int, float)):
        return credential
    if expires > time.time() * 1000 + RENEW_MARGIN_MS:
        return credential
    try:
        renewed = provider.oauth.refresh(credential)
    except LoginError:
        raise AuthError(
            f"Saved {provider.name} sign-in expired and could not be renewed."
            f" Run aider --login {provider.id} again."
        ) from None
    store.modify(provider.id, lambda current: renewed)
    return renewed


def apply_stored_keys(store, environ):
    """Copy stored keys into environ so litellm sees them (D9).

    Only stored credentials are copied. Environment values are already there.
    Returns the environment variable names that were set.
    """
    applied = []
    for provider_id in store.list():
        if provider_id not in PROVIDERS:
            continue
        stored = store.read(provider_id)
        if provider_id == "openai" and stored and stored.get("type") == "oauth":
            continue  # A ChatGPT token is not an OpenAI API key; models.py uses the auth file.
        try:
            resolved = resolve(provider_id, store, environ)
        except AuthError:
            continue  # Startup must not fail; the model step asks for a new login.
        if resolved and resolved.source == SOURCE_STORED:
            name = PROVIDERS[provider_id].env_var
            environ[name] = resolved.api_key
            applied.append(name)
    return applied


def login_api_key(provider_id, store, key):
    """Store an API key typed by the user, in the Pi api_key shape."""
    provider = get_provider(provider_id)
    key = (key or "").strip()
    if not key:
        raise AuthError("The API key is empty.")
    store.modify(provider.id, lambda current: {"type": "api_key", "key": key})
    return provider.env_var


def login_oauth(provider_id, store, interaction, environ):
    """Run the browser or headless OAuth flow and store the credential."""
    provider = get_provider(provider_id)
    if provider.oauth is None:
        raise AuthError(f"{provider.name} does not support browser sign-in. Use an API key.")
    credential = provider.oauth.login(interaction, environ=environ)
    store.modify(provider.id, lambda current: credential)
    return provider.env_var


def logout(provider_id, store):
    """Remove the stored credential only. Environment variables are not touched (Pi rule)."""
    get_provider(provider_id)
    if store.read(provider_id) is None:
        return False
    store.delete(provider_id)
    return True
