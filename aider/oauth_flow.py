"""Shared pieces of the browser sign-in flows for Anthropic and OpenAI.

Both flows follow the FineCode (Pi) OAuth pattern:

1. Start a loopback callback server on 127.0.0.1 with the provider's fixed port
   and path (only when the machine is local, decision D10).
2. Open the provider's authorization URL with PKCE (S256) and a `state`.
3. Accept the code from the browser callback, or from a redirect URL or code
   pasted by the user after a grace period, or when the machine is headless.
4. Exchange the code for tokens at the provider's token endpoint.

Standard library only (decision D0). Network access is injected by the caller,
so the flows can be tested without the internet.
"""

import base64
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from aider.openrouter_login import LoginError, challenge_for, generate_pkce, is_headless

__all__ = [
    "CallbackListener",
    "LoginError",
    "b64url",
    "challenge_for",
    "finish_login",
    "generate_pkce",
    "is_headless",
    "new_state",
    "parse_pasted",
    "post_request",
]

EXCHANGE_TIMEOUT_SECONDS = 30
LOGIN_TIMEOUT_SECONDS = 5 * 60
PASTE_FALLBACK_SECONDS = 60

_PAGE = (
    "<html><head><meta charset='utf-8'><title>aider</title></head>"
    "<body><h1>{title}</h1><p>{body}</p></body></html>"
)


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def new_state(nbytes=16):
    return secrets.token_hex(nbytes)


def post_request(url, body, form):
    """POST a form or JSON body and return the parsed JSON object.

    Error messages carry the HTTP status only, never the response body, so a
    token cannot leak into the terminal.
    """
    if form:
        data = urllib.parse.urlencode(body).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"
    else:
        data = json.dumps(body).encode("utf-8")
        content_type = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=EXCHANGE_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise LoginError(f"Token request to {_host(url)} failed (HTTP {error.code}).") from None
    except (urllib.error.URLError, OSError) as error:
        raise LoginError(f"Could not reach {_host(url)}: {error.__class__.__name__}.") from None
    try:
        parsed = json.loads(raw or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise LoginError(f"{_host(url)} returned an invalid response.") from None
    if not isinstance(parsed, dict):
        raise LoginError(f"{_host(url)} returned an invalid response.")
    return parsed


def _host(url):
    return urllib.parse.urlsplit(url).netloc


def parse_pasted(text, expected_state=None):
    """Return (code, state) from a bare code, `code#state`, or a redirect URL.

    A pasted state must match expected_state. A bare code has no state, so the
    PKCE verifier is the protection in that case.
    """
    value = (text or "").strip()
    if not value:
        raise LoginError("Nothing was pasted.")
    if "://" in value or "code=" in value:
        query = urllib.parse.urlsplit(value).query if "://" in value else value.lstrip("?")
        params = urllib.parse.parse_qs(query)
        code = params.get("code", [""])[0]
        state = params.get("state", [None])[0]
    elif "#" in value:
        code, state = value.split("#", 1)
    else:
        code, state = value, None
    if not code:
        raise LoginError("The pasted text has no authorization code.")
    if state is not None and expected_state is not None and state != expected_state:
        raise LoginError("The pasted code does not match this sign-in.")
    return code, state


def _page(title, body):
    return _PAGE.format(title=title, body=body).encode("utf-8")


class CallbackListener:
    """Loopback server that receives one authorization code.

    Requests with a wrong path or `state` are rejected and do not end the wait.
    The first valid code wins. A provider `error` ends the wait with LoginError.
    """

    def __init__(self, host, port, path, expected_state, redirect_host="localhost"):
        self._path = path
        self._state = expected_state
        self._event = threading.Event()
        self._code = None
        self._error = None
        self._lock = threading.Lock()
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def _send(self, status, title, body):
                payload = _page(title, body)
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):  # noqa: N802 - http.server naming
                listener._handle(self, self._send)

        self._server = ThreadingHTTPServer((host, port), Handler)
        self.port = self._server.server_address[1]
        self.redirect_uri = f"http://{redirect_host}:{self.port}{path}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _handle(self, request, send):
        parsed = urllib.parse.urlsplit(request.path)
        if parsed.path != self._path:
            send(404, "Not found", "This is not the aider sign-in callback.")
            return
        params = urllib.parse.parse_qs(parsed.query)
        if params.get("state", [None])[0] != self._state:
            send(400, "Sign-in rejected", "The request did not match this sign-in.")
            return
        with self._lock:
            if "error" in params:
                self._error = LoginError("The provider denied the sign-in or it was cancelled.")
                self._event.set()
                send(400, "Sign-in failed", "The provider did not authorize aider.")
                return
            code = params.get("code", [""])[0]
            if not code:
                send(400, "Sign-in failed", "The callback had no authorization code.")
                return
            if self._code is not None:
                send(409, "Already handled", "This sign-in has already completed.")
                return
            self._code = code
            self._event.set()
        send(200, "Signed in", "aider is signed in. You can close this tab.")

    def wait(self, timeout):
        """Return the code, or None if nothing arrived in time."""
        self._event.wait(timeout)
        with self._lock:
            if self._error is not None:
                raise self._error
            return self._code

    def close(self):
        self._server.shutdown()
        self._server.server_close()


def finish_login(
    interaction, listener, paste_message, expected_state, timeout=LOGIN_TIMEOUT_SECONDS
):
    """Wait for the code from the callback or from a paste, and return it.

    With a listener, the callback gets a grace period first. Then the user may
    paste a redirect URL or code. If nothing arrives, the callback gets the rest
    of the timeout. Without a listener only the paste is used.
    """
    try:
        if listener is not None:
            code = listener.wait(PASTE_FALLBACK_SECONDS)
            if code:
                return code
            interaction.notify(
                {
                    "type": "progress",
                    "message": "No callback from the browser yet. Paste the redirect URL or code"
                    " here to finish.",
                }
            )
        pasted = interaction.prompt(paste_message)
        if pasted and pasted.strip():
            code, _ = parse_pasted(pasted, expected_state)
            return code
        if listener is not None:
            code = listener.wait(timeout)
            if code:
                return code
        raise LoginError(
            "Sign-in timed out or no authorization code was received. Run the command again."
        )
    finally:
        if listener is not None:
            listener.close()
