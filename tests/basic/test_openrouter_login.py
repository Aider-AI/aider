import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer

import pytest

from aider import openrouter_login as ol
from aider.credential_store import CredentialStore
from aider.openrouter_login import (
    AlreadyClaimed,
    LoginError,
    challenge_for,
    exchange_code,
    generate_pkce,
    login,
    parse_pasted,
)

# RFC 7636, Appendix B.
RFC_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def _get(url):
    """Return the HTTP status of a GET, including error statuses."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def _auth_params(url):
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    return {name: values[0] for name, values in query.items()}


def _in_thread(function):
    thread = threading.Thread(target=function, daemon=True)
    thread.start()
    return thread


def _blocking_paste(cancel):
    """Behaves like a paste prompt the user never answers, until cancelled."""
    cancel.wait(10)
    return None


def _ok_post(code_seen):
    def post(url, payload, timeout):
        code_seen.append(payload)
        return 200, {"key": "sk-or-test-key"}

    return post


def test_challenge_matches_rfc7636_vector():
    assert challenge_for(RFC_VERIFIER) == RFC_CHALLENGE


def test_generated_pkce_has_expected_shape():
    verifier, challenge = generate_pkce()
    assert len(verifier) == 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", verifier)
    assert challenge == challenge_for(verifier)
    assert generate_pkce()[0] != verifier


def test_parse_pasted_accepts_bare_code():
    assert parse_pasted("  abc123  ") == ("abc123", None)


def test_parse_pasted_reads_code_and_state_from_url():
    assert parse_pasted("http://127.0.0.1:9/callback/x?code=c1&state=s1") == ("c1", "s1")


def test_parse_pasted_rejects_empty_and_codeless_input():
    with pytest.raises(LoginError):
        parse_pasted("   ")
    with pytest.raises(LoginError):
        parse_pasted("http://127.0.0.1:9/callback/x?state=s1")


def test_browser_callback_completes_login_with_pkce_verifier():
    payloads = []
    sent_challenge = {}

    def open_browser(url):
        params = _auth_params(url)
        sent_challenge["value"] = params["code_challenge"]

        def deliver():
            _get(f"{params['callback_url']}?code=good&state={params['state']}")

        _in_thread(deliver)

    key = login(open_browser, _blocking_paste, post_json=_ok_post(payloads), timeout=5)

    assert key == "sk-or-test-key"
    assert payloads[0]["code"] == "good"
    assert payloads[0]["code_challenge_method"] == "S256"
    # The verifier sent to the exchange must match the challenge sent to the browser.
    assert challenge_for(payloads[0]["code_verifier"]) == sent_challenge["value"]


def test_auth_url_carries_required_parameters():
    seen = {}

    def open_browser(url):
        seen.update(_auth_params(url))
        params = _auth_params(url)
        _in_thread(lambda: _get(f"{params['callback_url']}?code=c&state={params['state']}"))

    login(open_browser, _blocking_paste, post_json=_ok_post([]), timeout=5)

    assert seen["code_challenge_method"] == "S256"
    assert seen["callback_url"].startswith("http://127.0.0.1:")
    assert re.search(r"/callback/[A-Za-z0-9_-]+$", seen["callback_url"])
    assert len(seen["state"]) >= 40


def test_callback_with_wrong_state_is_rejected_and_login_continues():
    statuses = []
    deliveries = []

    def open_browser(url):
        params = _auth_params(url)

        def deliver():
            statuses.append(_get(f"{params['callback_url']}?code=forged&state=wrong"))
            statuses.append(_get(f"{params['callback_url']}?code=ok&state={params['state']}"))

        deliveries.append(_in_thread(deliver))

    key = login(open_browser, _blocking_paste, post_json=_ok_post([]), timeout=5)
    deliveries[0].join(timeout=5)  # login returns on success, before the 200 is recorded

    assert statuses == [400, 200]
    assert key == "sk-or-test-key"


def test_denied_callback_ends_login_at_once():
    def open_browser(url):
        params = _auth_params(url)
        denied = f"{params['callback_url']}?error=access_denied&state={params['state']}"
        _in_thread(lambda: _get(denied))

    started = time.monotonic()
    with pytest.raises(LoginError, match="denied"):
        login(open_browser, _blocking_paste, post_json=_ok_post([]), timeout=30)
    assert time.monotonic() - started < 10


def test_pasted_redirect_url_completes_login():
    payloads = []

    def read_paste(cancel):
        # The state is filled in by the test below, through the closure.
        return pasted["url"]

    pasted = {}

    def open_browser(url):
        params = _auth_params(url)
        pasted["url"] = f"{params['callback_url']}?code=pasted&state={params['state']}"

    key = login(open_browser, read_paste, post_json=_ok_post(payloads), timeout=5)

    assert key == "sk-or-test-key"
    assert payloads[0]["code"] == "pasted"


def test_pasted_url_with_wrong_state_is_rejected():
    def read_paste(cancel):
        return "http://127.0.0.1:9/callback/x?code=c&state=not-this-one"

    with pytest.raises(LoginError, match="does not match"):
        login(lambda url: None, read_paste, post_json=_ok_post([]), timeout=0.5)


def test_bad_paste_does_not_kill_a_valid_browser_callback():
    calls = []

    def post(url, payload, timeout):
        calls.append(payload["code"])
        if payload["code"] == "typo":
            return 403, {"error": "invalid code"}
        return 200, {"key": "sk-or-after-typo"}

    def read_paste(cancel):
        return "typo"

    def open_browser(url):
        params = _auth_params(url)

        def deliver():
            time.sleep(0.5)  # Let the bad paste fail first.
            _get(f"{params['callback_url']}?code=good&state={params['state']}")

        _in_thread(deliver)

    key = login(open_browser, read_paste, post_json=post, timeout=10)

    assert key == "sk-or-after-typo"
    assert calls[0] == "typo" and "good" in calls


def test_no_callback_and_no_paste_times_out_with_guidance():
    with pytest.raises(LoginError, match="timed out"):
        login(lambda url: None, _blocking_paste, post_json=_ok_post([]), timeout=0.3)


def test_callback_handler_returns_409_when_already_claimed(tmp_path):
    gate = ol._Gate()
    gate.claim()

    def complete(code):
        raise AlreadyClaimed("done")

    handler = ol._make_handler("/callback/p", "s", gate, complete)
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert _get(f"http://127.0.0.1:{port}/callback/p?code=x&state=s") == 409
        assert _get(f"http://127.0.0.1:{port}/callback/p?code=x&state=bad") == 400
        assert _get(f"http://127.0.0.1:{port}/callback/other?code=x&state=s") == 404
    finally:
        server.shutdown()
        server.server_close()


def test_gate_allows_one_claim_and_release_reopens_it():
    gate = ol._Gate()
    assert gate.claim() is True
    assert gate.claim() is False
    gate.release()
    assert gate.claim() is True


def test_exchange_maps_known_statuses_to_actionable_messages():
    def post_status(status):
        return lambda url, payload, timeout: (status, {"error": "x"})

    with pytest.raises(LoginError, match="expired"):
        exchange_code("c", "v", post_status(403))
    with pytest.raises(LoginError, match="HTTP 405"):
        exchange_code("c", "v", post_status(405))


def test_exchange_rejects_success_without_key():
    with pytest.raises(LoginError, match="did not contain a key"):
        exchange_code("c", "v", lambda url, payload, timeout: (200, {}))


def test_exchange_error_does_not_leak_code_or_verifier():
    def post(url, payload, timeout):
        return 403, {"error": "bad"}

    with pytest.raises(LoginError) as info:
        exchange_code("secret-code-123", "secret-verifier-456", post)
    assert "secret-code-123" not in str(info.value)
    assert "secret-verifier-456" not in str(info.value)


def test_is_headless_detects_ssh_and_missing_linux_display(monkeypatch):
    monkeypatch.setattr(ol.sys, "platform", "linux")
    assert ol.is_headless({"SSH_CONNECTION": "10.0.0.2 22 10.0.0.1 5000"}) is True
    assert ol.is_headless({}) is True
    assert ol.is_headless({"DISPLAY": ":0"}) is False
    assert ol.is_headless({"WAYLAND_DISPLAY": "wayland-0"}) is False


def test_is_headless_is_false_on_windows_and_macos_without_ssh(monkeypatch):
    for platform in ("win32", "darwin"):
        monkeypatch.setattr(ol.sys, "platform", platform)
        assert ol.is_headless({}) is False


def test_paste_only_uses_pasted_code_and_sends_no_callback():
    shown = []
    payloads = []

    def read_paste(cancel):
        return "pasted-code"

    key = ol.login_paste_only(read_paste, on_url=shown.append, post_json=_ok_post(payloads))

    assert key == "sk-or-test-key"
    assert payloads[0]["code"] == "pasted-code"
    assert "callback_url" not in shown[0]
    assert "state=" not in shown[0]
    assert "code_challenge_method=S256" in shown[0]


def test_paste_only_cancel_raises():
    with pytest.raises(LoginError, match="cancelled"):
        ol.login_paste_only(lambda cancel: None, on_url=lambda url: None, post_json=_ok_post([]))


class _Interaction:
    def __init__(self, paste_answer=None):
        self.events = []
        self.paste_answer = paste_answer
        self.prompts = []

    def notify(self, event):
        self.events.append(event)

    def prompt(self, message):
        self.prompts.append(message)
        return self.paste_answer


def test_openrouter_oauth_headless_pastes_code_and_returns_pi_credential():
    interaction = _Interaction(paste_answer="pasted-code")
    payloads = []
    credential = ol.OpenRouterOAuth().login(
        interaction, environ={"SSH_CONNECTION": "x"}, post_json=_ok_post(payloads)
    )
    assert credential == {
        "type": "oauth",
        "access": "sk-or-test-key",
        "refresh": "",
        "expires": 9007199254740991,
    }
    assert payloads[0]["code"] == "pasted-code"
    assert interaction.events[0]["type"] == "auth_url"
    assert "callback_url" not in interaction.events[0]["url"]


def test_openrouter_oauth_local_uses_callback_and_never_prompts(monkeypatch):
    monkeypatch.setattr(ol.sys, "platform", "win32")
    interaction = _Interaction()

    def open_browser(url):
        params = _auth_params(url)
        _in_thread(lambda: _get(f"{params['callback_url']}?code=c&state={params['state']}"))

    credential = ol.OpenRouterOAuth().login(
        interaction, environ={}, open_browser=open_browser, post_json=_ok_post([])
    )
    assert credential["access"] == "sk-or-test-key"
    assert interaction.prompts == []


def test_openrouter_oauth_refresh_and_to_auth_follow_pi_contract():
    oauth = ol.OpenRouterOAuth()
    credential = ol.credential_from_key("sk-or-x")
    assert oauth.refresh(credential) == credential
    assert oauth.to_auth(credential) == {"apiKey": "sk-or-x"}


def test_paste_fallback_completes_login_after_grace_without_callback():
    seen = {}

    def open_browser(url):
        seen.update(_auth_params(url))  # no callback is ever sent

    def ask_paste(message):
        return f"{seen['callback_url']}?code=pasted-after-grace&state={seen['state']}"

    payloads = []
    key = login(
        open_browser,
        on_url=lambda url: None,
        timeout=5,
        post_json=_ok_post(payloads),
        ask_paste=ask_paste,
        grace_seconds=0.2,
    )
    assert key == "sk-or-test-key"
    assert payloads[0]["code"] == "pasted-after-grace"


def test_enter_at_fallback_keeps_waiting_for_the_callback():
    seen = {}

    def open_browser(url):
        seen.update(_auth_params(url))

        def late_callback():
            time.sleep(0.5)
            _get(f"{seen['callback_url']}?code=late&state={seen['state']}")

        _in_thread(late_callback)

    key = login(
        open_browser,
        on_url=lambda url: None,
        timeout=5,
        post_json=_ok_post([]),
        ask_paste=lambda message: "",
        grace_seconds=0.2,
    )
    assert key == "sk-or-test-key"


def test_no_callback_and_no_paste_times_out_after_fallback():
    with pytest.raises(LoginError, match="timed out"):
        login(
            lambda url: None,
            on_url=lambda url: None,
            timeout=0.5,
            post_json=_ok_post([]),
            ask_paste=lambda message: "",
            grace_seconds=0.2,
        )


def test_callback_events_report_outcome_without_secrets():
    events = []

    def open_browser(url):
        params = _auth_params(url)

        def deliver():
            _get(f"{params['callback_url']}?code=forged&state=wrong")
            _get(f"{params['callback_url']}?code=ok&state={params['state']}")

        _in_thread(deliver)

    login(
        open_browser,
        _blocking_paste,
        on_url=lambda url: None,
        timeout=5,
        post_json=_ok_post([]),
        on_event=events.append,
    )
    assert any("state did not match" in message for message in events)
    assert any("Exchanging" in message for message in events)
