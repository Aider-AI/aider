import pytest

from aider import auth
from aider.credential_store import CredentialStore


def _store(tmp_path):
    return CredentialStore(tmp_path / "auth.json")


def _oauth_credential(key):
    return {"type": "oauth", "access": key, "refresh": "", "expires": 9007199254740991}


class FakeOAuth:
    def __init__(self, key):
        self.key = key
        self.calls = []

    def login(self, interaction, environ=None):
        self.calls.append(environ)
        return _oauth_credential(self.key)

    def refresh(self, credential):
        return credential

    def to_auth(self, credential):
        return {"apiKey": credential["access"]}


class _Interaction:
    def notify(self, event):
        pass

    def prompt(self, message):
        return None


def test_registry_declares_methods_per_provider():
    assert auth.get_provider("openrouter").methods == ("browser", "key")
    assert auth.get_provider("openai").methods == ("browser", "key")
    assert auth.get_provider("anthropic").methods == ("browser", "key")
    assert auth.get_provider("deepseek").methods == ("key",)
    assert auth.get_provider("openrouter").env_var == "OPENROUTER_API_KEY"


def test_unknown_provider_is_an_auth_error():
    with pytest.raises(auth.AuthError, match="Unknown provider"):
        auth.get_provider("nope")


def test_stored_oauth_credential_beats_environment(tmp_path):
    store = _store(tmp_path)
    store.modify("openrouter", lambda current: _oauth_credential("sk-stored"))
    resolved = auth.resolve("openrouter", store, {"OPENROUTER_API_KEY": "sk-env"})
    assert resolved.api_key == "sk-stored"
    assert resolved.source == auth.SOURCE_STORED


def test_stored_api_key_beats_environment(tmp_path):
    store = _store(tmp_path)
    store.modify("openai", lambda current: {"type": "api_key", "key": "sk-stored"})
    resolved = auth.resolve("openai", store, {"OPENAI_API_KEY": "sk-env"})
    assert resolved.api_key == "sk-stored"
    assert resolved.source == auth.SOURCE_STORED


def test_environment_is_used_only_when_nothing_is_stored(tmp_path):
    resolved = auth.resolve("openai", _store(tmp_path), {"OPENAI_API_KEY": "sk-env"})
    assert resolved.api_key == "sk-env"
    assert resolved.source == auth.SOURCE_ENV


def test_nothing_stored_and_no_environment_resolves_to_none(tmp_path):
    assert auth.resolve("openai", _store(tmp_path), {}) is None


def test_apply_stored_keys_copies_only_stored_credentials(tmp_path):
    store = _store(tmp_path)
    store.modify("openrouter", lambda current: _oauth_credential("sk-stored"))
    environ = {"OPENAI_API_KEY": "sk-env-openai"}
    applied = auth.apply_stored_keys(store, environ)
    assert applied == ["OPENROUTER_API_KEY"]
    assert environ["OPENROUTER_API_KEY"] == "sk-stored"
    assert environ["OPENAI_API_KEY"] == "sk-env-openai"


def test_login_api_key_stores_pi_api_key_shape(tmp_path):
    store = _store(tmp_path)
    auth.login_api_key("openai", store, "  sk-typed  ")
    assert store.read("openai") == {"type": "api_key", "key": "sk-typed"}


def test_login_api_key_rejects_empty_input(tmp_path):
    with pytest.raises(auth.AuthError, match="empty"):
        auth.login_api_key("openai", _store(tmp_path), "   ")


def test_login_oauth_stores_credential_from_provider(tmp_path, monkeypatch):
    fake = FakeOAuth("sk-browser")
    monkeypatch.setitem(
        auth.PROVIDERS, "openrouter", auth.ProviderAuth(
            id="openrouter", name="openrouter", env_var="OPENROUTER_API_KEY",
            oauth=fake, methods=("browser", "key"),
        ),
    )
    store = _store(tmp_path)
    auth.login_oauth("openrouter", store, _Interaction(), {"X": "1"})
    assert store.read("openrouter") == _oauth_credential("sk-browser")
    assert fake.calls == [{"X": "1"}]


def test_login_oauth_refuses_providers_without_browser_sign_in(tmp_path):
    with pytest.raises(auth.AuthError, match="does not support browser"):
        auth.login_oauth("deepseek", _store(tmp_path), _Interaction(), {})


def test_logout_removes_only_the_stored_credential(tmp_path):
    store = _store(tmp_path)
    store.modify("openai", lambda current: {"type": "api_key", "key": "sk-stored"})
    environ = {"OPENAI_API_KEY": "sk-env"}
    assert auth.logout("openai", store) is True
    assert store.read("openai") is None
    assert auth.resolve("openai", store, environ).source == auth.SOURCE_ENV


def test_logout_without_stored_credential_returns_false(tmp_path):
    assert auth.logout("openai", _store(tmp_path)) is False


def test_logout_unknown_provider_is_an_auth_error(tmp_path):
    with pytest.raises(auth.AuthError):
        auth.logout("nope", _store(tmp_path))
