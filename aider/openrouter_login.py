"""Sign in to OpenRouter from the terminal and store the resulting API key.

Flow (OpenRouter OAuth PKCE, https://openrouter.ai/docs/use-cases/oauth-pkce):

1. Create a PKCE verifier and its S256 challenge, and a random `state`.
2. Start a callback server on 127.0.0.1 with a random port and path.
3. Open https://openrouter.ai/auth with callback_url, code_challenge,
   code_challenge_method=S256 and state.
4. Accept whichever arrives first: the browser callback, or a code or redirect
   URL pasted by the user (needed over SSH or in containers).
5. Exchange the code at https://openrouter.ai/api/v1/auth/keys with the
   verifier. The response carries the key.

Rules:

- A callback whose `state` does not match is rejected with 400 and does not
  consume the login. A forged request cannot end someone else's sign-in.
- Only one code is exchanged per login. A second callback gets 409.
- A pasted URL that carries a `state` must match it. A bare pasted code has no
  state, so PKCE is the protection in that case.
- The wait is bounded (5 minutes by default), and the caller can cancel it.
- No error message includes the key, the verifier or the code.

Dependencies are standard library only (decision D0). Network and browser
access are injected, so the flow can be tested without the internet.

The public surface is OpenRouterOAuth: login(interaction), refresh and to_auth,
the same shape as Pi's OAuthAuth. The interaction object is the only link to
the terminal (notify for events, prompt for pasted input).
"""

import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTHORIZE_URL = "https://openrouter.ai/auth"
TOKEN_URL = "https://openrouter.ai/api/v1/auth/keys"
LOGIN_TIMEOUT_SECONDS = 5 * 60
PASTE_FALLBACK_SECONDS = 60
EXCHANGE_TIMEOUT_SECONDS = 30
PROVIDER = "openrouter"

EXCHANGE_HINTS = {
    400: "OpenRouter rejected code_challenge_method. This is a bug in aider.",
    403: "OpenRouter rejected the code or verifier, or the code expired (codes last 10 minutes).",
    405: "OpenRouter rejected the request method or protocol.",
}


class LoginError(Exception):
    """A sign-in step failed. The message is safe to show to the user."""


class AlreadyClaimed(LoginError):
    """Another code already won this sign-in. Not a failure of the attempt."""


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def challenge_for(verifier):
    """S256 code challenge for a verifier (RFC 7636, section 4.2)."""
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def generate_pkce():
    """Return (verifier, challenge). 32 random bytes give a 43-character verifier."""
    verifier = _b64url(secrets.token_bytes(32))
    return verifier, challenge_for(verifier)


def parse_pasted(text):
    """Return (code, state) from a bare code or a full redirect URL.

    `state` is None when the paste carries no state. Raises LoginError when
    the text is empty or holds no code.
    """
    value = (text or "").strip()
    if not value:
        raise LoginError("Nothing was pasted.")
    if "://" in value or value.startswith("?") or "code=" in value:
        query = urllib.parse.urlsplit(value).query if "://" in value else value.lstrip("?")
        params = urllib.parse.parse_qs(query)
        code = params.get("code", [""])[0]
        state = params.get("state", [None])[0]
        if not code:
            raise LoginError("The pasted URL has no authorization code.")
        return code, state
    return value, None


def _post_json(url, payload, timeout):
    """POST JSON and return (status, parsed_body). Network errors raise LoginError."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _parse_body(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _parse_body(error.read())
    except (urllib.error.URLError, OSError) as error:
        raise LoginError(f"Could not reach OpenRouter: {error.__class__.__name__}.") from None


def _parse_body(raw):
    try:
        parsed = json.loads(raw or b"{}")
    except (ValueError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def exchange_code(code, verifier, post_json=_post_json):
    """Trade an authorization code for an API key."""
    status, body = post_json(
        TOKEN_URL,
        {"code": code, "code_verifier": verifier, "code_challenge_method": "S256"},
        EXCHANGE_TIMEOUT_SECONDS,
    )
    if status != 200:
        hint = EXCHANGE_HINTS.get(status, "Unexpected response from OpenRouter.")
        raise LoginError(f"Key exchange failed (HTTP {status}). {hint}")
    key = body.get("key")
    if not isinstance(key, str) or not key:
        raise LoginError("OpenRouter's response did not contain a key.")
    return key


class _Gate:
    """One sign-in attempt.

    A code is claimed before it is exchanged, so only one exchange runs. If an
    exchange fails, the claim is released and the attempt keeps waiting: a
    mistyped paste must not kill a browser callback that is still valid.
    Only an explicit denial from the browser ends the attempt at once.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._claimed = False
        self._done = threading.Event()
        self.key = None
        self.denied = None
        self.last_error = None

    def claim(self):
        with self._lock:
            if self._claimed or self._done.is_set():
                return False
            self._claimed = True
            return True

    def release(self):
        with self._lock:
            if not self._done.is_set():
                self._claimed = False

    def is_claimed(self):
        with self._lock:
            return self._claimed or self._done.is_set()

    def succeed(self, key):
        self.key = key
        self._done.set()

    def deny(self, error):
        self.denied = error
        self._done.set()

    def note(self, error):
        self.last_error = error

    def wait(self, timeout):
        return self._done.wait(timeout)


_PAGE = (
    "<html><head><meta charset='utf-8'><title>aider</title></head>"
    "<body><h1>{title}</h1><p>{body}</p></body></html>"
)


def _page(title, body):
    # Text is plain ASCII from this module; no user input is echoed.
    return _PAGE.format(title=title, body=body).encode("utf-8")


def _make_handler(path, state, gate, complete, on_event=None):
    emit = on_event or (lambda message: None)

    class CallbackHandler(BaseHTTPRequestHandler):
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
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path != path:
                emit("Callback: request for an unknown path (ignored).")
                self._send(404, "Not found", "This is not the aider sign-in callback.")
                return
            params = urllib.parse.parse_qs(parsed.query)
            if params.get("state", [None])[0] != state:
                emit("Callback: the state did not match this sign-in (ignored).")
                self._send(400, "Sign-in rejected", "The request did not match this sign-in.")
                return
            if "error" in params:
                emit("Callback: OpenRouter denied the sign-in.")
                gate.deny(LoginError("OpenRouter sign-in was denied or cancelled."))
                self._send(400, "Sign-in failed", "OpenRouter did not authorize aider.")
                return
            code = params.get("code", [""])[0]
            if not code:
                emit("Callback: no authorization code in the request (ignored).")
                self._send(400, "Sign-in failed", "The callback had no authorization code.")
                return
            emit("Callback received. Exchanging the code for a key...")
            try:
                complete(code)
            except AlreadyClaimed:
                emit("Callback: this sign-in already completed.")
                self._send(409, "Already handled", "This sign-in has already completed.")
                return
            except LoginError as error:
                emit(f"Callback: key exchange failed. {error}")
                gate.note(error)
                self._send(502, "Sign-in failed", "Key exchange failed. Check the terminal.")
                return
            self._send(200, "Signed in", "aider is signed in to OpenRouter. Close this tab.")

    return CallbackHandler


def login(
    open_browser,
    read_paste=None,
    on_url=print,
    timeout=LOGIN_TIMEOUT_SECONDS,
    host="127.0.0.1",
    post_json=_post_json,
    on_event=None,
    ask_paste=None,
    grace_seconds=PASTE_FALLBACK_SECONDS,
):
    """Run the sign-in and return the API key.

    open_browser(url): opens the authorization URL. Failures are ignored.
    read_paste(cancel_event): concurrent paste (used by tests and the thread
        path). It must be cancellable. Pass None to disable it.
    on_event(message): progress messages, without secrets.
    ask_paste(message): a blocking prompt used once, after grace_seconds with
        no callback. Pressing Enter (empty input) keeps waiting for the callback.
        A pasted redirect URL is checked against state and then exchanged.
    """
    verifier, challenge = generate_pkce()
    state = secrets.token_urlsafe(32)
    path = "/callback/" + secrets.token_urlsafe(16)
    gate = _Gate()

    def complete(code):
        if not gate.claim():
            raise AlreadyClaimed("This sign-in has already completed.")
        try:
            key = exchange_code(code, verifier, post_json)
        except LoginError:
            gate.release()
            raise
        gate.succeed(key)
        return key

    emit = on_event or (lambda message: None)
    server = HTTPServer((host, 0), _make_handler(path, state, gate, complete, on_event))
    redirect_uri = f"http://{host}:{server.server_address[1]}{path}"
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    cancel = threading.Event()
    paste_thread = None
    try:
        query = urllib.parse.urlencode(
            {
                "callback_url": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )
        url = f"{AUTHORIZE_URL}?{query}"
        on_url(url)
        try:
            open_browser(url)
        except Exception:
            pass  # The URL is already printed for manual use.

        def paste_worker():
            text = read_paste(cancel)
            if text is None or cancel.is_set():
                return
            try:
                code, pasted_state = parse_pasted(text)
                if pasted_state is not None and pasted_state != state:
                    raise LoginError("The pasted URL does not match this sign-in.")
                complete(code)
            except AlreadyClaimed:
                return
            except LoginError as error:
                gate.note(error)

        if read_paste is not None:
            paste_thread = threading.Thread(target=paste_worker, daemon=True)
            paste_thread.start()

        def timed_out():
            detail = f" Last error: {gate.last_error}" if gate.last_error else ""
            return LoginError(f"Sign-in timed out. Run the command again to retry.{detail}")

        started = time.monotonic()
        if not gate.wait(grace_seconds if ask_paste is not None else timeout):
            if ask_paste is None:
                raise timed_out()
            emit(
                "No callback from the browser yet. Paste the redirect URL from the browser's"
                " address bar to finish, or press Enter to keep waiting."
            )
            text = ask_paste("Redirect URL: ")
            if text and text.strip():
                try:
                    code, pasted_state = parse_pasted(text)
                    if pasted_state is not None and pasted_state != state:
                        raise LoginError("The pasted URL does not match this sign-in.")
                    complete(code)
                except AlreadyClaimed:
                    pass
                except LoginError as error:
                    gate.note(error)
                    emit(f"Pasted URL: {error}")
            remaining = max(0.0, timeout - (time.monotonic() - started))
            if not gate.wait(remaining):
                raise timed_out()
        if gate.denied is not None:
            raise gate.denied
        return gate.key
    finally:
        cancel.set()
        server.shutdown()
        server.server_close()


def is_headless(environ):
    """True when a browser on this machine cannot reach a loopback callback.

    Remote shells (SSH) and Linux sessions with no display are treated as
    headless. macOS and Windows are treated as local.
    """
    if any(environ.get(name) for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
        return True
    on_linux = sys.platform.startswith("linux")
    return on_linux and not (environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))


def login_paste_only(read_paste, on_url=print, post_json=_post_json):
    """Headless sign-in: show the URL, then wait for the pasted code.

    No callback server runs, so there is no race with other input. The code
    is single-use and expires after 10 minutes (OpenRouter docs).
    """
    verifier, challenge = generate_pkce()
    query = urllib.parse.urlencode({"code_challenge": challenge, "code_challenge_method": "S256"})
    on_url(f"{AUTHORIZE_URL}?{query}")
    text = read_paste(threading.Event())
    if text is None:
        raise LoginError("Sign-in cancelled.")
    code, _ = parse_pasted(text)
    return exchange_code(code, verifier, post_json)


class OpenRouterOAuth:
    """OpenRouter as a Pi-style OAuth provider.

    login(interaction): browser callback on a local machine, pasted code when
    headless (D10). Returns an oauth credential in the Pi shape.
    """

    name = "OpenRouter OAuth"

    def login(self, interaction, environ=None, open_browser=webbrowser.open, post_json=_post_json):
        environ = os.environ if environ is None else environ
        if is_headless(environ):
            key = login_paste_only(
                read_paste=lambda cancel: interaction.prompt("Paste the code or redirect URL: "),
                on_url=lambda url: interaction.notify({"type": "auth_url", "url": url}),
                post_json=post_json,
            )
        else:
            key = login(
                open_browser=open_browser,
                read_paste=None,  # no concurrent paste locally (D10)
                on_url=lambda url: interaction.notify({"type": "auth_url", "url": url}),
                post_json=post_json,
                on_event=lambda message: interaction.notify(
                    {"type": "progress", "message": message}
                ),
                ask_paste=lambda message: interaction.prompt(message),
            )
        return credential_from_key(key)

    def refresh(self, credential):
        # OpenRouter keys do not expire on their own, so there is nothing to refresh.
        return credential

    def to_auth(self, credential):
        return {"apiKey": credential["access"]}


def credential_from_key(key):
    """Pi credential shape for an OpenRouter key. The key never expires by itself."""
    return {"type": "oauth", "access": key, "refresh": "", "expires": 9007199254740991}

