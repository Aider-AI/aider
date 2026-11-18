import urllib.parse
import urllib.request

import pytest

from aider import auth
from aider.anthropic_login import AnthropicOAuth, CLIENT_ID, COPY_CODE_REDIRECT_URI, TOKEN_URL
from aider.credential_store import CredentialStore
from aider.oauth_flow import CallbackListener, LoginError

HEADLESS = {"SSH_CONNECTION": "10.0.0.1 22 10.0.0.2 2222"}


class FakeInteraction:
    def __init__(self, paste=None):
        self.events = []
        self.paste = paste
        self.prompts = []

    def notify(self, event):
        self.events.append(event)

    def prompt(self, message):
        self.prompts.append(message)
        return self.paste(self) if callable(self.paste) else self.paste


def _state_from(interaction):
    url = next(e["url"] for e in interaction.events if e["type"] == "auth_url")
    return urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)


def _tokens(**overrides):
    data = {"access_token": "sk-ant-oat01-new", "refresh_token": "r-new", "expires_in": 3600}
    data.update(overrides)
    return data


def test_headless_login_exchanges_code_and_stores_oauth_shape():
    calls = []

    def post(url, body, form):
        calls.append((url, body, form))
        return _tokens()

    interaction = FakeInteraction(paste=lambda i: "abc#" + _state_from(i)["state"][0])
    credential = AnthropicOAuth().login(interaction, environ=HEADLESS, post=post)

    assert credential["type"] == "oauth"
    assert credential["access"] == "sk-ant-oat01-new"
    assert credential["refresh"] == "r-new"
    assert credential["expires"] > 0

    url, body, form = calls[0]
    assert url == TOKEN_URL and form is False
    assert body["grant_type"] == "authorization_code"
    assert body["client_id"] == CLIENT_ID
    assert body["code"] == "abc"
    assert body["redirect_uri"] == COPY_CODE_REDIRECT_URI
    assert body["state"] == body["code_verifier"]


def test_authorization_url_matches_finecode_parameters():
    interaction = FakeInteraction(paste=lambda i: "abc#" + _state_from(i)["state"][0])
    AnthropicOAuth().login(interaction, environ=HEADLESS, post=lambda *a: _tokens())
    query = _state_from(interaction)

    assert query["client_id"] == [CLIENT_ID]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code"] == ["true"]
    assert query["redirect_uri"] == [COPY_CODE_REDIRECT_URI]
    assert "user:inference" in query["scope"][0]


def test_pasted_state_must_match():
    interaction = FakeInteraction(paste="abc#not-the-state")
    with pytest.raises(LoginError, match="does not match"):
        AnthropicOAuth().login(interaction, environ=HEADLESS, post=lambda *a: _tokens())


def test_empty_paste_is_rejected():
    interaction = FakeInteraction(paste="   ")
    with pytest.raises(LoginError):
        AnthropicOAuth().login(interaction, environ=HEADLESS, post=lambda *a: _tokens())


def test_refresh_uses_refresh_token_and_keeps_old_one_when_missing():
    calls = []

    def post(url, body, form):
        calls.append(body)
        return _tokens(refresh_token=None)

    old = {"type": "oauth", "access": "old", "refresh": "r-old", "expires": 0}
    renewed = AnthropicOAuth().refresh(old, post=post)

    assert calls[0]["grant_type"] == "refresh_token"
    assert calls[0]["refresh_token"] == "r-old"
    assert renewed["access"] == "sk-ant-oat01-new"
    assert renewed["refresh"] == "r-old"


def test_to_auth_returns_access_token_as_api_key():
    credential = {"type": "oauth", "access": "tok", "refresh": "r", "expires": 1}
    assert AnthropicOAuth().to_auth(credential) == {"apiKey": "tok"}


def test_expired_stored_credential_is_renewed_on_resolve(tmp_path, monkeypatch):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify(
        "anthropic",
        lambda current: {"type": "oauth", "access": "old", "refresh": "r-old", "expires": 0},
    )
    provider = auth.get_provider("anthropic")
    monkeypatch.setattr(
        provider.oauth,
        "refresh",
        lambda credential: {"type": "oauth", "access": "fresh", "refresh": "r2", "expires": 9e15},
    )

    resolved = auth.resolve("anthropic", store, {})

    assert resolved.api_key == "fresh"
    assert store.read("anthropic")["access"] == "fresh"


def test_failed_renewal_raises_auth_error_and_startup_skips_it(tmp_path, monkeypatch):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify(
        "anthropic",
        lambda current: {"type": "oauth", "access": "old", "refresh": "r-old", "expires": 0},
    )
    provider = auth.get_provider("anthropic")

    def fail(credential):
        raise LoginError("network down")

    monkeypatch.setattr(provider.oauth, "refresh", fail)
    environ = {}

    with pytest.raises(auth.AuthError, match="aider --login anthropic"):
        auth.resolve("anthropic", store, environ)
    assert auth.apply_stored_keys(store, environ) == []
    assert "ANTHROPIC_API_KEY" not in environ


def test_callback_listener_accepts_code_with_matching_state():
    listener = CallbackListener("127.0.0.1", 0, "/callback", "st-1")
    try:
        url = f"http://127.0.0.1:{listener.port}/callback?code=xyz&state=st-1"
        urllib.request.urlopen(url).read()
        assert listener.wait(5) == "xyz"
    finally:
        listener.close()


def test_callback_listener_ignores_wrong_state():
    listener = CallbackListener("127.0.0.1", 0, "/callback", "st-1")
    try:
        with pytest.raises(Exception):
            urllib.request.urlopen(f"http://127.0.0.1:{listener.port}/callback?code=xyz&state=bad")
        assert listener.wait(0.1) is None
    finally:
        listener.close()


def test_callback_listener_reports_provider_denial():
    listener = CallbackListener("127.0.0.1", 0, "/callback", "st-1")
    try:
        with pytest.raises(Exception):
            urllib.request.urlopen(
                f"http://127.0.0.1:{listener.port}/callback?error=access_denied&state=st-1"
            )
        with pytest.raises(LoginError):
            listener.wait(5)
    finally:
        listener.close()

