"""Terminal sign-in shared by `aider --login` and the in-chat /login and /logout.

Both entry points call the same functions, so the flow and the messages match.
"""

from aider import auth
from aider.credential_store import CredentialStore


class TerminalInteraction:
    """The link between the auth layer and the user (decision D3).

    `output` and `ask` default to print and input. In chat, pass the io object's
    methods so messages and prompts go through the chat interface.
    """

    def __init__(self, output=print, ask=input):
        self._output = output
        self._ask = ask

    def notify(self, event):
        if event.get("type") == "auth_url":
            self._output(f"Open this URL to sign in:\n{event['url']}")
        elif event.get("type") == "progress":
            self._output(event["message"])

    def prompt(self, message):
        try:
            return self._ask(message)
        except (EOFError, KeyboardInterrupt):
            return None


def choose(question, options, ask=input, output=print):
    """Ask for one of options by number or name. Returns the chosen name."""
    for number, option in enumerate(options, start=1):
        output(f"  {number}. {option}")
    answer = (ask(f"{question} ") or "").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(options):
        return options[int(answer) - 1]
    if answer in options:
        return answer
    raise auth.AuthError(f"'{answer}' is not one of: {', '.join(options)}.")


def login_provider(
    provider, method, store, interaction, environ, getpass_fn, ask=input, output=print
):
    """Sign in to a provider and store the credential. Returns (provider, method).

    With no provider, the user picks one. With no method, the browser is used when
    the provider supports it (the default sign-in); otherwise the API key. Pass
    method="key" to type a key instead. Raises AuthError or LoginError on failure.
    """
    if provider is None:
        provider = choose("Provider to sign in to:", list(auth.PROVIDERS), ask, output)
    provider_auth = auth.get_provider(provider)
    if method is None:
        method = "browser" if "browser" in provider_auth.methods else provider_auth.methods[0]
    if method == "browser":
        auth.login_oauth(provider, store, interaction, environ)
    elif method == "key":
        key = getpass_fn(f"API key for {provider_auth.name} (input is hidden): ")
        auth.login_api_key(provider, store, key)
    else:
        raise auth.AuthError(f"Unknown method '{method}'. Use browser or key.")
    return provider, method


def use_now(provider, store, environ):
    """Make a just-stored key visible to litellm in this running process (D9)."""
    resolved = auth.resolve(provider, store, environ)
    if resolved is not None:
        environ[auth.get_provider(provider).env_var] = resolved.api_key


def logout_provider(provider, store):
    """Remove the stored credential. Returns True if one was removed."""
    return auth.logout(provider, store)


def default_store():
    return CredentialStore()
