import pytest

from aider import auth, login_cli
from aider.credential_store import CredentialStore


def _store(tmp_path):
    return CredentialStore(tmp_path / "auth.json")


def test_choose_accepts_number_or_name():
    assert login_cli.choose("q", ["a", "b"], ask=lambda _: "2", output=lambda _: None) == "b"
    assert login_cli.choose("q", ["a", "b"], ask=lambda _: "a", output=lambda _: None) == "a"


def test_choose_rejects_unknown_answer():
    with pytest.raises(auth.AuthError):
        login_cli.choose("q", ["a", "b"], ask=lambda _: "zzz", output=lambda _: None)


def test_login_provider_api_key_stores_credential(tmp_path):
    store = _store(tmp_path)
    provider, method = login_cli.login_provider(
        "openai", "key", store, login_cli.TerminalInteraction(output=lambda m: None), {},
        getpass_fn=lambda prompt: "sk-typed",
    )
    assert (provider, method) == ("openai", "key")
    assert store.read("openai") == {"type": "api_key", "key": "sk-typed"}


def test_login_provider_single_method_needs_no_question(tmp_path):
    asked = []
    login_cli.login_provider(
        "deepseek", None, _store(tmp_path), login_cli.TerminalInteraction(output=lambda m: None),
        {}, getpass_fn=lambda prompt: "sk-typed",
        ask=lambda q: asked.append(q) or "",
    )
    assert asked == []


def test_login_provider_asks_only_provider_and_defaults_to_browser(tmp_path, monkeypatch):
    number = str(list(auth.PROVIDERS).index("anthropic") + 1)
    answers = iter([number])
    started = []
    monkeypatch.setattr(
        auth, "login_oauth", lambda provider, store, interaction, environ: started.append(provider)
    )
    provider, method = login_cli.login_provider(
        None, None, _store(tmp_path), login_cli.TerminalInteraction(output=lambda m: None), {},
        getpass_fn=lambda prompt: "sk-typed", ask=lambda q: next(answers),
        output=lambda m: None,
    )
    assert (provider, method) == ("anthropic", "browser")
    assert started == ["anthropic"]


def test_login_provider_key_needs_explicit_method(tmp_path):
    provider, method = login_cli.login_provider(
        "openai", "key", _store(tmp_path), login_cli.TerminalInteraction(output=lambda m: None),
        {}, getpass_fn=lambda prompt: "sk-typed", ask=lambda q: "", output=lambda m: None,
    )
    assert (provider, method) == ("openai", "key")


def test_use_now_exposes_stored_key_to_this_process(tmp_path):
    store = _store(tmp_path)
    store.modify("openai", lambda current: {"type": "api_key", "key": "sk-stored"})
    environ = {}
    login_cli.use_now("openai", store, environ)
    assert environ["OPENAI_API_KEY"] == "sk-stored"


def test_logout_provider_reports_whether_anything_was_removed(tmp_path):
    store = _store(tmp_path)
    store.modify("openai", lambda current: {"type": "api_key", "key": "k"})
    assert login_cli.logout_provider("openai", store) is True
    assert login_cli.logout_provider("openai", store) is False
