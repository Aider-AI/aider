import json
import os
import stat

import pytest

from aider import credential_store
from aider.credential_store import CredentialStore, CredentialStoreError, env_name_for_provider

posix_only = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")


def _oauth(key):
    return {"type": "oauth", "access": key, "refresh": "", "expires": 9007199254740991}


def test_missing_file_reads_as_empty(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    assert store.read("openrouter") is None
    assert store.list() == []
    assert not (tmp_path / "auth.json").exists()


def test_modify_round_trip(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openrouter", lambda current: _oauth("sk-or-test"))
    assert store.read("openrouter") == _oauth("sk-or-test")


def test_modify_replaces_one_entry_on_repeated_login(tmp_path):
    path = tmp_path / "auth.json"
    store = CredentialStore(path)
    store.modify("openrouter", lambda current: _oauth("first"))
    store.modify("openrouter", lambda current: _oauth("second"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data) == ["openrouter"]
    assert store.read("openrouter")["access"] == "second"


def test_modify_receives_current_value(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openai", lambda current: {"type": "api_key", "key": "k1"})
    seen = []
    store.modify("openai", lambda current: seen.append(current) or current)
    assert seen == [{"type": "api_key", "key": "k1"}]


def test_modify_returning_none_removes_entry(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openrouter", lambda current: _oauth("a"))
    store.modify("openrouter", lambda current: None)
    assert store.read("openrouter") is None


def test_providers_are_kept_separate_and_listed_sorted(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openrouter", lambda current: _oauth("a"))
    store.modify("anthropic", lambda current: {"type": "api_key", "key": "b"})
    assert store.list() == ["anthropic", "openrouter"]
    assert store.read("anthropic")["type"] == "api_key"


def test_delete_removes_entry_and_ignores_missing(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openrouter", lambda current: _oauth("a"))
    store.delete("openrouter")
    assert store.read("openrouter") is None
    store.delete("openrouter")  # no error on a missing entry


def test_list_never_returns_secrets(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.modify("openrouter", lambda current: _oauth("sk-or-secret"))
    assert "sk-or-secret" not in repr(store.list())


@posix_only
def test_file_is_created_with_mode_0600(tmp_path):
    path = tmp_path / "auth.json"
    CredentialStore(path).modify("openrouter", lambda current: _oauth("a"))
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


@posix_only
def test_directory_is_created_with_mode_0700(tmp_path):
    directory = tmp_path / "newdir"
    CredentialStore(directory / "auth.json").modify("openrouter", lambda current: _oauth("a"))
    assert stat.S_IMODE(os.stat(directory).st_mode) == 0o700


def test_corrupt_file_raises_and_is_not_overwritten(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("{not json", encoding="utf-8")
    store = CredentialStore(path)
    with pytest.raises(CredentialStoreError):
        store.modify("openrouter", lambda current: _oauth("a"))
    assert path.read_text(encoding="utf-8") == "{not json"


def test_non_object_json_raises(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(CredentialStoreError):
        CredentialStore(path).read("openrouter")


def test_failed_replace_keeps_previous_file_and_leaves_no_temp_files(tmp_path, monkeypatch):
    path = tmp_path / "auth.json"
    store = CredentialStore(path)
    store.modify("openrouter", lambda current: _oauth("original"))
    before = path.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("simulated crash during replace")

    monkeypatch.setattr(credential_store.os, "replace", boom)
    with pytest.raises(OSError):
        store.modify("openrouter", lambda current: _oauth("new"))

    assert path.read_text(encoding="utf-8") == before
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_raising_update_function_writes_nothing(tmp_path):
    path = tmp_path / "auth.json"
    store = CredentialStore(path)
    with pytest.raises(RuntimeError):
        store.modify("openrouter", lambda current: (_ for _ in ()).throw(RuntimeError("x")))
    assert not path.exists()


def test_default_path_is_under_home_aider(monkeypatch, tmp_path):
    monkeypatch.setattr(credential_store.Path, "home", classmethod(lambda cls: tmp_path))
    store = CredentialStore()
    assert store.path == tmp_path / ".aider" / "auth.json"


def test_env_name_for_provider():
    assert env_name_for_provider("openrouter") == "OPENROUTER_API_KEY"
