"""Provider authentication in the Pi pattern: API key or browser OAuth.

A provider declares the ways it can be signed in to (`api_key` and/or `oauth`).
Stored credentials own a provider: resolve() only consults the environment when
nothing is stored (decision D1). Resolved keys reach litellm through
os.environ, because that is how aider already passes keys (decision D9).

Explicit --api-key flags are applied later in main() and still win.
"""

from dataclasses import dataclass, field

from aider.credential_store import env_name_for_provider
from aider.openrouter_login import OpenRouterOAuth

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


def _build_providers():
    providers = {}
    for provider_id, env_var in API_KEY_PROVIDERS.items():
        providers[provider_id] = ProviderAuth(
            id=provider_id,
            name=provider_id,
            env_var=env_var,
            oauth=OpenRouterOAuth() if provider_id == "openrouter" else None,
            methods=("browser", "key") if provider_id == "openrouter" else ("key",),
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
            key = provider.oauth.to_auth(stored).get("apiKey")
        else:
            key = stored.get("key")
        if key:
            return Resolved(api_key=key, source=SOURCE_STORED)
    value = environ.get(provider.env_var)
    if value:
        return Resolved(api_key=value, source=SOURCE_ENV)
    return None


def apply_stored_keys(store, environ):
    """Copy stored keys into environ so litellm sees them (D9).

    Only stored credentials are copied. Environment values are already there.
    Returns the environment variable names that were set.
    """
    applied = []
    for provider_id in store.list():
        if provider_id not in PROVIDERS:
            continue
        resolved = resolve(provider_id, store, environ)
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


def env_name(provider_id):
    return env_name_for_provider(provider_id)
