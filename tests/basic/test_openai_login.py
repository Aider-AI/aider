import base64
import json
import urllib.parse

import pytest

from aider.oauth_flow import LoginError
from aider.openai_login import (
    AUTHORIZE_URL,
    CLIENT_ID,
    JWT_CLAIM_PATH,
    REDIRECT_URI,
    TOKEN_URL,
    OpenAICodexOAuth,
)

HEADLESS = {"SSH_CONNECTION": "10.0.0.1 22 10.0.0.2 2222"}


class FakeInteraction:
    def __init__(self, paste=None):
        self.events = []
        self.paste = paste

    def notify(self, event):
        self.events.append(event)

    def prompt(self, message):
        return self.paste(self) if callable(self.paste) else self.paste


def _jwt(account_id="acc-123"):
    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    claims = {JWT_CLAIM_PATH: {"chatgpt_account_id": account_id}} if account_id else {}
    return f"{b64({'alg': 'none'})}.{b64(claims)}.sig"


def _paste_for(interaction, code="c1"):
    state = _state_from(interaction)[1]["state"][0]
    return f"{REDIRECT_URI}?code={code}&state={state}"


def _state_from(interaction):
    url = next(e["url"] for e in interaction.events if e["type"] == "auth_url")
    return url, urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)


def _tokens(access=None, **overrides):
    data = {"access_token": access or _jwt(), "refresh_token": "r-new", "expires_in": 3600}
    data.update(overrides)
    return data


def test_authorization_url_matches_finecode_parameters():
    interaction = FakeInteraction(paste=_paste_for)
    OpenAICodexOAuth().login(interaction, environ=HEADLESS, post=lambda *a: _tokens())
    url, query = _state_from(interaction)

    assert url.startswith(AUTHORIZE_URL + "?")
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["code_challenge_method"] == ["S256"]
    assert query["codex_cli_simplified_flow"] == ["true"]
    assert query["originator"] == ["pi"]
    assert len(query["state"][0]) == 32


def test_paste_exchanges_code_with_verifier_and_stores_account_id():
    calls = []

    def post(url, body, form):
        calls.append((url, body, form))
        return _tokens()

    interaction = FakeInteraction(paste=_paste_for)
    credential = OpenAICodexOAuth().login(interaction, environ=HEADLESS, post=post)

    url, body, form = calls[0]
    assert url == TOKEN_URL and form is True
    assert body["grant_type"] == "authorization_code"
    assert body["code"] == "c1"
    assert body["redirect_uri"] == REDIRECT_URI
    assert body["code_verifier"]
    assert credential["type"] == "oauth"
    assert credential["refresh"] == "r-new"
    assert credential["accountId"] == "acc-123"


def test_paste_with_wrong_state_is_rejected():
    interaction = FakeInteraction(paste=REDIRECT_URI + "?code=c1&state=wrong")
    with pytest.raises(LoginError, match="does not match"):
        OpenAICodexOAuth().login(interaction, environ=HEADLESS, post=lambda *a: _tokens())


def test_token_without_account_id_is_rejected():
    interaction = FakeInteraction(paste=_paste_for)
    with pytest.raises(LoginError, match="account ID"):
        OpenAICodexOAuth().login(
            interaction, environ=HEADLESS, post=lambda *a: _tokens(access=_jwt(account_id=None))
        )


def test_refresh_posts_form_with_refresh_token():
    calls = []

    def post(url, body, form):
        calls.append((body, form))
        return _tokens()

    old = {
        "type": "oauth",
        "access": "old",
        "refresh": "r-old",
        "expires": 0,
        "accountId": "acc-123",
    }
    renewed = OpenAICodexOAuth().refresh(old, post=post)

    body, form = calls[0]
    assert form is True
    assert body["grant_type"] == "refresh_token"
    assert body["refresh_token"] == "r-old"
    assert body["client_id"] == CLIENT_ID
    assert renewed["accountId"] == "acc-123"


def test_to_auth_returns_access_token_as_api_key():
    credential = {"type": "oauth", "access": "tok", "refresh": "r", "expires": 1, "accountId": "a"}
    assert OpenAICodexOAuth().to_auth(credential) == {"apiKey": "tok"}
