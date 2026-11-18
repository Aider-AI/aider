"""Sign in to OpenAI with a ChatGPT Plus/Pro subscription, by browser, as FineCode does.

Source of the flow: FineCode packages/ai/src/auth/oauth/openai-codex.ts (browser login).

- Authorization: https://auth.openai.com/oauth/authorize with PKCE (S256) and a
  random `state`. Parameters match FineCode.
- Local machine: the browser returns to http://localhost:1455/auth/callback. If
  port 1455 is busy (the Codex CLI or another login), the user pastes the URL.
- Token exchange and refresh: form POST to https://auth.openai.com/oauth/token.
- The account ID is read from the access token's JWT claim
  https://api.openai.com/auth, chatgpt_account_id.

Warning: the client ID belongs to another application (Codex CLI). It was copied
from FineCode at the owner's explicit request, and OpenAI may restrict or revoke
it. The access token is for the ChatGPT backend (chatgpt.com/backend-api), not
api.openai.com, so it is only used through the chatgpt/ models (aider/oauth_runtime.py).
"""

import base64
import json
import os
import time
import urllib.parse
import webbrowser

from aider.oauth_flow import (
    CallbackListener,
    LoginError,
    finish_login,
    generate_pkce,
    is_headless,
    new_state,
    post_request,
)

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_HOST = "localhost"
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 1455
CALLBACK_PATH = "/auth/callback"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
SCOPE = "openid profile email offline_access"
ORIGINATOR = "pi"  # value FineCode sends by default
JWT_CLAIM_PATH = "https://api.openai.com/auth"


def _account_id(access_token):
    """Return chatgpt_account_id from the access token's JWT, or None."""
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (IndexError, ValueError, TypeError):
        return None
    auth = claims.get(JWT_CLAIM_PATH) if isinstance(claims, dict) else None
    account = auth.get("chatgpt_account_id") if isinstance(auth, dict) else None
    return account if isinstance(account, str) and account else None


def _credential(data):
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    expires_in = data.get("expires_in")
    if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
        raise LoginError("OpenAI's token response is missing the access or refresh token.")
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise LoginError("OpenAI's token response has an invalid expires_in.")
    account_id = _account_id(access)
    if account_id is None:
        raise LoginError("Could not read the ChatGPT account ID from OpenAI's access token.")
    return {
        "type": "oauth",
        "access": access,
        "refresh": refresh,
        "expires": int(time.time() * 1000 + expires_in * 1000),
        "accountId": account_id,
    }


class OpenAICodexOAuth:
    name = "OpenAI (ChatGPT Plus/Pro)"

    def login(self, interaction, environ=None, open_browser=webbrowser.open, post=post_request):
        environ = os.environ if environ is None else environ
        verifier, challenge = generate_pkce()
        state = new_state()

        listener = None
        if not is_headless(environ):
            try:
                listener = CallbackListener(
                    CALLBACK_HOST, CALLBACK_PORT, CALLBACK_PATH, state, redirect_host=REDIRECT_HOST
                )
            except OSError:
                listener = None  # Port 1455 is busy: the user pastes the redirect URL.

        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "originator": ORIGINATOR,
        }
        url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
        interaction.notify(
            {
                "type": "auth_url",
                "url": url,
                "instructions": "Complete login in your browser. If the browser is on another"
                " machine, paste the final redirect URL here.",
            }
        )
        if listener is not None:
            try:
                open_browser(url)
            except Exception:
                pass  # The URL is already shown for manual use.

        code = finish_login(
            interaction,
            listener,
            "Paste the redirect URL or authorization code here (or wait for the browser): ",
            state,
        )
        interaction.notify(
            {"type": "progress", "message": "Exchanging authorization code for tokens..."}
        )
        data = post(
            TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": REDIRECT_URI,
            },
            True,
        )
        return _credential(data)

    def refresh(self, credential, post=post_request):
        data = post(
            TOKEN_URL,
            {
                "grant_type": "refresh_token",
                "refresh_token": credential["refresh"],
                "client_id": CLIENT_ID,
            },
            True,
        )
        return _credential(data)

    def to_auth(self, credential):
        return {"apiKey": credential["access"]}
