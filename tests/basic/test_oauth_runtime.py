import base64
import json
import os
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aider import auth, oauth_runtime
from aider.credential_store import CredentialStore
from aider.llm import litellm

OAT = "sk-ant-oat01-test-token"

CODEX_SSE = (
    'data: {"type":"response.output_text.delta","delta":"hi","item_id":"m1",'
    '"output_index":0,"content_index":0}\n\n'
    'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
    '"created_at":1,"model":"gpt-5-codex","status":"completed","output":[{"type":"message",'
    '"id":"m1","role":"assistant","status":"completed","content":[{"type":"output_text",'
    '"text":"hi","annotations":[]}]}],"usage":{"input_tokens":1,"output_tokens":1,'
    '"total_tokens":2}}}\n\n'
)


def _jwt_with_exp(exp):
    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{b64({'alg': 'none'})}.{b64({'exp': exp})}.sig"


class _Recorder:
    """Local HTTP stub that records every POST. Nothing leaves the machine."""

    def __init__(self, status=200, body=None, sse=None):
        self.requests = []
        self.status = status
        self.body = body
        self.sse = sse

    def start(self):
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("content-length", 0))
                raw = self.rfile.read(length)
                recorder.requests.append(
                    {
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": json.loads(raw or b"{}"),
                    }
                )
                if recorder.sse is not None:
                    payload = recorder.sse.encode()
                    content_type = "text/event-stream"
                else:
                    payload = json.dumps(recorder.body or {"error": "test"}).encode()
                    content_type = "application/json"
                self.send_response(recorder.status)
                self.send_header("content-type", content_type)
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def anthropic_server():
    recorder = _Recorder(
        body={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-4-5",
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    ).start()
    yield recorder
    recorder.stop()


def test_anthropic_oauth_call_detection():
    oauth_env = {"ANTHROPIC_API_KEY": OAT}
    assert oauth_runtime.is_anthropic_oauth_call("anthropic/claude-sonnet-4-5", oauth_env)
    assert oauth_runtime.is_anthropic_oauth_call("claude-sonnet-4-5", oauth_env)
    api_env = {"ANTHROPIC_API_KEY": "sk-ant-api03"}
    assert not oauth_runtime.is_anthropic_oauth_call("anthropic/x", api_env)
    assert not oauth_runtime.is_anthropic_oauth_call("openai/gpt-5", oauth_env)


def test_anthropic_adjustments_add_identity_beta_and_user_agent():
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    new_messages, headers = oauth_runtime.anthropic_oauth_adjustments(
        messages, {"anthropic-beta": "prompt-caching-2024-07-31"}
    )
    assert new_messages[0] == {"role": "system", "content": oauth_runtime.CLAUDE_CODE_IDENTITY}
    assert new_messages[1:] == messages
    assert "claude-code-20250219" in headers["anthropic-beta"]
    assert "prompt-caching-2024-07-31" in headers["anthropic-beta"]
    assert headers["user-agent"].startswith("claude-cli/")
    assert headers["x-app"] == "cli"


def test_anthropic_oauth_token_goes_out_as_bearer_with_claude_code_identity(
    anthropic_server, monkeypatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", OAT)
    messages, headers = oauth_runtime.anthropic_oauth_adjustments(
        [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}], None
    )
    litellm.completion(
        model="anthropic/claude-sonnet-4-5",
        messages=messages,
        api_base=anthropic_server.url,
        api_key=OAT,
        extra_headers=headers,
        max_tokens=16,
    )

    request = anthropic_server.requests[0]
    assert request["headers"]["authorization"] == f"Bearer {OAT}"
    assert "x-api-key" not in request["headers"]
    assert "oauth-2025-04-20" in request["headers"]["anthropic-beta"]
    assert "claude-code-20250219" in request["headers"]["anthropic-beta"]
    assert request["headers"]["user-agent"].startswith("claude-cli/")
    assert "You are Claude Code, Anthropic" in json.dumps(request["body"]["system"])


def test_chatgpt_requires_browser_sign_in(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openai", lambda current: {"type": "api_key", "key": "sk-api"})
    with pytest.raises(auth.AuthError, match="aider --login openai"):
        oauth_runtime.prepare_chatgpt_auth(store, {"AIDER_CHATGPT_TOKEN_DIR": str(tmp_path / "c")})
    assert not (tmp_path / "c" / "auth.json").exists()


def test_chatgpt_auth_file_is_written_from_store_with_private_mode(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    future = int(time.time()) + 3600
    store.modify(
        "openai",
        lambda current: {
            "type": "oauth",
            "access": _jwt_with_exp(future),
            "refresh": "r-1",
            "expires": future * 1000,
            "accountId": "acc-9",
        },
    )
    environ = {"AIDER_CHATGPT_TOKEN_DIR": str(tmp_path / "chatgpt")}
    path = oauth_runtime.prepare_chatgpt_auth(store, environ)

    data = json.loads(path.read_text())
    assert data["refresh_token"] == "r-1"
    assert data["account_id"] == "acc-9"
    assert data["expires_at"] == future
    assert environ["CHATGPT_TOKEN_DIR"] == str(tmp_path / "chatgpt")
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_chatgpt_renews_an_expiring_token_before_writing(tmp_path, monkeypatch):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify(
        "openai",
        lambda current: {
            "type": "oauth",
            "access": "old",
            "refresh": "r-old",
            "expires": 0,
            "accountId": "acc-9",
        },
    )
    fresh = _jwt_with_exp(int(time.time()) + 3600)
    monkeypatch.setattr(
        auth.get_provider("openai").oauth,
        "refresh",
        lambda credential: {
            "type": "oauth",
            "access": fresh,
            "refresh": "r-new",
            "expires": int(time.time() * 1000) + 3600_000,
            "accountId": "acc-9",
        },
    )
    environ = {"AIDER_CHATGPT_TOKEN_DIR": str(tmp_path / "c")}
    path = oauth_runtime.prepare_chatgpt_auth(store, environ)
    assert json.loads(path.read_text())["access_token"] == fresh


def test_sync_copies_back_a_token_litellm_rotated(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify(
        "openai",
        lambda current: {
            "type": "oauth",
            "access": "a1",
            "refresh": "r1",
            "expires": 1,
            "accountId": "x",
        },
    )
    directory = tmp_path / "c"
    directory.mkdir()
    (directory / "auth.json").write_text(
        json.dumps(
            {
                "access_token": "a2",
                "refresh_token": "r2",
                "expires_at": 4102444800,
                "account_id": "x",
            }
        )
    )
    environ = {"AIDER_CHATGPT_TOKEN_DIR": str(directory)}

    assert oauth_runtime.sync_chatgpt_auth(store, environ) is True
    stored = store.read("openai")
    assert stored["access"] == "a2"
    assert stored["refresh"] == "r2"
    assert stored["expires"] == 4102444800 * 1000


def test_chatgpt_model_name_is_bridged_to_responses():
    bridge = oauth_runtime.chatgpt_completion_model
    assert bridge("chatgpt/gpt-5-codex") == "chatgpt/responses/gpt-5-codex"
    assert bridge("chatgpt/responses/gpt-5-codex") == "chatgpt/responses/gpt-5-codex"


def test_chatgpt_call_carries_bearer_and_account_id(tmp_path, monkeypatch):
    recorder = _Recorder(status=200, sse=CODEX_SSE).start()
    try:
        future = int(time.time()) + 3600
        token = _jwt_with_exp(future)
        store = CredentialStore(tmp_path / "auth.json")
        store.modify(
            "openai",
            lambda current: {
                "type": "oauth",
                "access": token,
                "refresh": "r-1",
                "expires": future * 1000,
                "accountId": "acc-9",
            },
        )
        monkeypatch.setenv("CHATGPT_API_BASE", recorder.url)
        monkeypatch.setenv("AIDER_CHATGPT_TOKEN_DIR", str(tmp_path / "c"))
        monkeypatch.setenv("CHATGPT_TOKEN_DIR", str(tmp_path / "c"))
        oauth_runtime.prepare_chatgpt_auth(store, os.environ)

        response = litellm.completion(
            model=oauth_runtime.chatgpt_completion_model("chatgpt/gpt-5-codex"),
            messages=[{"role": "user", "content": "hi"}],
            stream=False,
            max_retries=0,
        )

        request = recorder.requests[0]
        assert request["path"].endswith("/responses")
        assert request["headers"]["authorization"] == f"Bearer {token}"
        assert request["headers"]["chatgpt-account-id"] == "acc-9"
        assert response.choices[0].message.content == "hi"
    finally:
        recorder.stop()


def _capture_completion(monkeypatch):
    import aider.models as models_module

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return {"choices": []}

    monkeypatch.setattr(models_module.litellm, "completion", fake_completion)
    return calls


def test_send_completion_adds_claude_code_identity_for_oauth_token(monkeypatch):
    from aider.models import Model

    calls = _capture_completion(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", OAT)
    model = Model("anthropic/claude-sonnet-4-5", verbose=False)
    model.send_completion([{"role": "user", "content": "hi"}], None, False, temperature=0)

    sent = calls[0]
    assert sent["messages"][0]["content"] == oauth_runtime.CLAUDE_CODE_IDENTITY
    assert "claude-code-20250219" in sent["extra_headers"]["anthropic-beta"]


def test_send_completion_leaves_api_keys_alone(monkeypatch):
    from aider.models import Model

    calls = _capture_completion(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-plain")
    model = Model("anthropic/claude-sonnet-4-5", verbose=False)
    model.send_completion([{"role": "user", "content": "hi"}], None, False, temperature=0)

    assert calls[0]["messages"][0]["role"] == "user"
    assert "extra_headers" not in calls[0] or "claude-code" not in str(calls[0]["extra_headers"])


def test_send_completion_routes_chatgpt_through_responses_and_writes_auth(tmp_path, monkeypatch):
    from aider.models import Model

    calls = _capture_completion(monkeypatch)
    future = int(time.time()) + 3600
    store_path = tmp_path / "auth.json"
    CredentialStore(store_path).modify(
        "openai",
        lambda current: {
            "type": "oauth",
            "access": _jwt_with_exp(future),
            "refresh": "r-1",
            "expires": future * 1000,
            "accountId": "acc-9",
        },
    )
    import aider.credential_store as cs

    monkeypatch.setattr(cs, "CredentialStore", lambda *a, **k: CredentialStore(store_path))
    monkeypatch.setattr(oauth_runtime, "CHATGPT_TOKEN_DIR", tmp_path / "chatgpt")
    monkeypatch.delenv("AIDER_CHATGPT_TOKEN_DIR", raising=False)

    model = Model("chatgpt/gpt-5-codex", verbose=False)
    model.send_completion([{"role": "user", "content": "hi"}], None, False, temperature=None)

    assert calls[0]["model"] == "chatgpt/responses/gpt-5-codex"
    assert (tmp_path / "chatgpt" / "auth.json").exists()
