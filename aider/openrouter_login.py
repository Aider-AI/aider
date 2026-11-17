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
"""

import base64
import hashlib
import json
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTHORIZE_URL = "https://openrouter.ai/auth"
TOKEN_URL = "https://openrouter.ai/api/v1/auth/keys"
LOGIN_TIMEOUT_SECONDS = 5 * 60
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


def _make_handler(path, state, gate, complete):
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
                self._send(404, "Not found", "This is not the aider sign-in callback.")
                return
            params = urllib.parse.parse_qs(parsed.query)
            if params.get("state", [None])[0] != state:
                self._send(400, "Sign-in rejected", "The request did not match this sign-in.")
                return
            if "error" in params:
                gate.deny(LoginError("OpenRouter sign-in was denied or cancelled."))
                self._send(400, "Sign-in failed", "OpenRouter did not authorize aider.")
                return
            code = params.get("code", [""])[0]
            if not code:
                self._send(400, "Sign-in failed", "The callback had no authorization code.")
                return
            try:
                complete(code)
            except AlreadyClaimed:
                self._send(409, "Already handled", "This sign-in has already completed.")
                return
            except LoginError as error:
                gate.note(error)
                self._send(502, "Sign-in failed", "Key exchange failed. Check the terminal.")
                return
            self._send(200, "Signed in", "aider is signed in to OpenRouter. Close this tab.")

    return CallbackHandler


def login(
    open_browser,
    read_paste,
    on_url=print,
    timeout=LOGIN_TIMEOUT_SECONDS,
    host="127.0.0.1",
    post_json=_post_json,
):
    """Run the sign-in and return the API key.

    open_browser(url): opens the authorization URL. Failures are ignored.
    read_paste(cancel_event): blocks until the user pastes text or until
        cancel_event is set, then returns the text or None. The caller must
        make this cancellable, or the wait will hold the terminal.
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

    server = HTTPServer((host, 0), _make_handler(path, state, gate, complete))
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

        paste_thread = threading.Thread(target=paste_worker, daemon=True)
        paste_thread.start()

        if not gate.wait(timeout):
            detail = f" Last error: {gate.last_error}" if gate.last_error else ""
            raise LoginError(f"Sign-in timed out. Run the command again to retry.{detail}")
        if gate.denied is not None:
            raise gate.denied
        return gate.key
    finally:
        cancel.set()
        server.shutdown()
        server.server_close()


def login_and_store(store, open_browser, read_paste, **kwargs):
    """Run the sign-in and save the key as the OpenRouter credential."""
    key = login(open_browser, read_paste, **kwargs)
    store.set(PROVIDER, "oauth", key)
    return key


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


def run_login(store, environ, open_browser, read_paste, on_url=print, post_json=_post_json):
    """Sign in with the mode that fits this machine, then store the key.

    Local: the browser callback is the only path. Pasting is off, because a
    blocked terminal read cannot be cancelled and would take the next input line.
    Headless: pasting is the only path.
    """
    if is_headless(environ):
        key = login_paste_only(read_paste, on_url=on_url, post_json=post_json)
    else:
        key = login(
            open_browser,
            lambda cancel: None,
            on_url=on_url,
            post_json=post_json,
        )
    store.set(PROVIDER, "oauth", key)
    return key
