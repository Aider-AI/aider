import json
import os
import stat

import pytest

from aider import credential_store
from aider.credential_store import CredentialStore, CredentialStoreError

posix_only = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")


def test_missing_file_reads_as_empty(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    assert store.get("openrouter") is None
    assert store.providers() == []
    assert not (tmp_path / "auth.json").exists()


def test_set_then_get_round_trip(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.set("openrouter", "oauth", "sk-or-test")
    assert store.get("openrouter") == {"type": "oauth", "key": "sk-or-test"}


def test_one_entry_per_provider_on_repeated_login(tmp_path):
    path = tmp_path / "auth.json"
    store = CredentialStore(path)
    store.set("openrouter", "oauth", "first")
    store.set("openrouter", "oauth", "second")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data) == ["openrouter"]
    assert store.get("openrouter")["key"] == "second"


def test_providers_are_kept_separate(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.set("openrouter", "oauth", "a")
    store.set("anthropic", "api_key", "b")
    assert store.providers() == ["anthropic", "openrouter"]
    assert store.get("anthropic")["type"] == "api_key"


def test_delete_removes_entry_and_ignores_missing(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.set("openrouter", "oauth", "a")
    store.delete("openrouter")
    assert store.get("openrouter") is None
    store.delete("openrouter")  # no error on a missing entry


def test_providers_never_returns_key_values(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.set("openrouter", "oauth", "sk-or-secret")
    assert "sk-or-secret" not in repr(store.providers())


@posix_only
def test_file_is_created_with_mode_0600(tmp_path):
    path = tmp_path / "auth.json"
    CredentialStore(path).set("openrouter", "oauth", "a")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


@posix_only
def test_directory_is_created_with_mode_0700(tmp_path):
    directory = tmp_path / "newdir"
    CredentialStore(directory / "auth.json").set("openrouter", "oauth", "a")
    assert stat.S_IMODE(os.stat(directory).st_mode) == 0o700


def test_corrupt_file_raises_and_is_not_overwritten(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("{not json", encoding="utf-8")
    store = CredentialStore(path)
    with pytest.raises(CredentialStoreError):
        store.set("openrouter", "oauth", "a")
    assert path.read_text(encoding="utf-8") == "{not json"


def test_non_object_json_raises(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(CredentialStoreError):
        CredentialStore(path).get("openrouter")


def test_failed_replace_keeps_previous_file_and_leaves_no_temp_files(tmp_path, monkeypatch):
    path = tmp_path / "auth.json"
    store = CredentialStore(path)
    store.set("openrouter", "oauth", "original")
    before = path.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("simulated crash during replace")

    monkeypatch.setattr(credential_store.os, "replace", boom)
    with pytest.raises(OSError):
        store.set("openrouter", "oauth", "new")

    assert path.read_text(encoding="utf-8") == before
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_empty_key_is_rejected(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    with pytest.raises(ValueError):
        store.set("openrouter", "oauth", "")
    assert not (tmp_path / "auth.json").exists()


def test_default_path_is_under_home_aider(monkeypatch, tmp_path):
    monkeypatch.setattr(credential_store.Path, "home", classmethod(lambda cls: tmp_path))
    store = CredentialStore()
    assert store.path == tmp_path / ".aider" / "auth.json"


def test_stored_key_replaces_env_and_dotenv_values(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    store.set("openrouter", "oauth", "sk-or-stored")
    environ = {"OPENROUTER_API_KEY": "sk-or-from-env", "OTHER": "kept"}

    applied = credential_store.apply_stored_credentials(store, environ)

    assert applied == ["OPENROUTER_API_KEY"]
    assert environ["OPENROUTER_API_KEY"] == "sk-or-stored"
    assert environ["OTHER"] == "kept"


def test_no_stored_credentials_leaves_environ_alone(tmp_path):
    store = CredentialStore(tmp_path / "auth.json")
    environ = {"OPENROUTER_API_KEY": "sk-or-from-env"}
    assert credential_store.apply_stored_credentials(store, environ) == []
    assert environ == {"OPENROUTER_API_KEY": "sk-or-from-env"}


def test_env_name_for_provider():
    assert credential_store.env_name_for_provider("openrouter") == "OPENROUTER_API_KEY"
