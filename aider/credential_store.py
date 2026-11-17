"""Persistent provider credentials for aider.

One JSON file holds one entry per provider:

    {"openrouter": {"type": "oauth", "key": "..."}}

Guarantees (see docs/login-roadmap.md, D2):

- The file is created with mode 0600 on POSIX, inside a 0700 directory.
- Writes are atomic: a temporary file in the same directory is fsynced and
  then moved over the target with os.replace. A failed write leaves the
  previous file intact.
- A corrupt file is never overwritten. Reading it raises CredentialStoreError,
  so a damaged file cannot silently erase stored keys.
- Writing a provider replaces its entry. Repeated logins do not add entries.
- Key values are never included in error messages.

Limits:

- On Windows, file modes are not enforced (os.chmod only sets the read-only
  flag). The file is still written atomically, but its access is governed by
  the user profile ACLs.
- Concurrent writers within one process are serialized with a lock. Across
  processes the last writer wins, which is acceptable for one interactive user.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

CREDENTIAL_FILE_NAME = "auth.json"
FILE_MODE = 0o600
DIR_MODE = 0o700


class CredentialStoreError(Exception):
    """The credential file exists but cannot be read as a valid store."""


class CredentialStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".aider" / CREDENTIAL_FILE_NAME
        self._lock = threading.Lock()

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CredentialStoreError(
                f"Credential file {self.path} is unreadable or corrupt"
                f" ({error.__class__.__name__}). It was not modified."
                " Move it aside to start over."
            ) from None
        if not isinstance(data, dict):
            raise CredentialStoreError(
                f"Credential file {self.path} does not contain a JSON object."
                " It was not modified."
            )
        return data

    def _save(self, data):
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(directory, DIR_MODE)

        fd, temp_name = tempfile.mkstemp(dir=directory, prefix=".auth-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if os.name == "posix":
                os.chmod(temp_name, FILE_MODE)
            os.replace(temp_name, self.path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def get(self, provider):
        """Return the stored entry for a provider, or None."""
        with self._lock:
            return self._load().get(provider)

    def set(self, provider, credential_type, key):
        """Store or replace the entry for a provider."""
        if not provider or not key:
            raise ValueError("provider and key are required")
        with self._lock:
            data = self._load()
            data[provider] = {"type": credential_type, "key": key}
            self._save(data)

    def delete(self, provider):
        """Remove a provider entry. Missing entries are ignored."""
        with self._lock:
            data = self._load()
            if provider not in data:
                return
            del data[provider]
            self._save(data)

    def providers(self):
        """Provider names with stored entries. Never returns key values."""
        with self._lock:
            return sorted(self._load())


def env_name_for_provider(provider):
    """OpenRouter -> OPENROUTER_API_KEY, the variable aider already reads."""
    return f"{provider.upper()}_API_KEY"


def apply_stored_credentials(store, environ):
    """Copy stored keys into environ, replacing any value already there.

    Stored credentials win over .env files and shell variables (D1). Explicit
    --api-key flags are applied later in main() and still win over this.
    Returns the environment variable names that were set.
    """
    applied = []
    for provider in store.providers():
        entry = store.get(provider)
        if not entry or not entry.get("key"):
            continue
        name = env_name_for_provider(provider)
        environ[name] = entry["key"]
        applied.append(name)
    return applied
