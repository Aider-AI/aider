"""Sign in to Anthropic (Claude Pro/Max) by browser, as FineCode does.

Source of the flow: FineCode packages/ai/src/auth/oauth/anthropic.ts.

- Authorization: https://claude.ai/oauth/authorize with PKCE (S256). `state` is
  the PKCE verifier, as in FineCode.
- Local machine: the browser returns to http://localhost:53692/callback, which
  the loopback listener receives. If that port is busy, a free port is used.
- Headless machine: the code is shown by Anthropic on platform.claude.com and
  pasted back as `code#state`.
- Token exchange and refresh: JSON POST to https://platform.claude.com/v1/oauth/token.

Warning: the client ID belongs to another application (Claude Code). It was
copied from FineCode at the owner's explicit request, and Anthropic may restrict
or revoke it. Subscription tokens go out as Bearer tokens with the Claude Code
identity (aider/oauth_runtime.py).
"""

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
    post_request,
)

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 53692
CALLBACK_PATH = "/callback"
COPY_CODE_REDIRECT_URI = "https://platform.claude.com/oauth/code/callback"
SCOPES = (
    "org:create_api_key user:profile user:inference user:sessions:claude_code"
    " user:mcp_servers user:file_upload"
)
EXPIRY_MARGIN_MS = 5 * 60 * 1000


def _credential(data, previous_refresh=None):
    access = data.get("access_token")
    refresh = data.get("refresh_token") or previous_refresh
    expires_in = data.get("expires_in")
    if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
        raise LoginError("Anthropic's token response is missing the access or refresh token.")
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise LoginError("Anthropic's token response has an invalid expires_in.")
    return {
        "type": "oauth",
        "access": access,
        "refresh": refresh,
        "expires": int(time.time() * 1000 + expires_in * 1000 - EXPIRY_MARGIN_MS),
    }


def _exchange(code, state, verifier, redirect_uri, post):
    data = post(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "state": state,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        False,
    )
    return _credential(data)


class AnthropicOAuth:
    name = "Anthropic (Claude Pro/Max)"

    def login(self, interaction, environ=None, open_browser=webbrowser.open, post=post_request):
        environ = os.environ if environ is None else environ
        verifier, challenge = generate_pkce()
        headless = is_headless(environ)

        listener = None
        if headless:
            redirect_uri = COPY_CODE_REDIRECT_URI
        else:
            redirect_uri = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"
            for port in (CALLBACK_PORT, 0):
                try:
                    listener = CallbackListener(
                        CALLBACK_HOST, port, CALLBACK_PATH, verifier, redirect_host="localhost"
                    )
                    redirect_uri = listener.redirect_uri
                    break
                except OSError:
                    continue

        params = {
            "code": "true",
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": verifier,
        }
        url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
        if headless:
            instructions = (
                "Complete login in your browser, then copy the code Anthropic shows"
                " and paste it here."
            )
            paste_message = "Paste the code Anthropic shows after you sign in (code#state): "
        else:
            instructions = (
                "Complete login in your browser. If the browser is on another machine,"
                " paste the final redirect URL here."
            )
            paste_message = "Paste the redirect URL or code here (or wait for the browser): "
        interaction.notify({"type": "auth_url", "url": url, "instructions": instructions})
        if not headless:
            try:
                open_browser(url)
            except Exception:
                pass  # The URL is already shown for manual use.

        code = finish_login(interaction, listener, paste_message, verifier)
        interaction.notify(
            {"type": "progress", "message": "Exchanging authorization code for tokens..."}
        )
        return _exchange(code, verifier, verifier, redirect_uri, post)

    def refresh(self, credential, post=post_request):
        data = post(
            TOKEN_URL,
            {
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": credential["refresh"],
            },
            False,
        )
        return _credential(data, previous_refresh=credential["refresh"])

    def to_auth(self, credential):
        return {"apiKey": credential["access"]}

