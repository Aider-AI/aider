"""Persistent provider credentials for aider.

One JSON file holds one credential per provider, in the Pi format:

    {"openrouter": {"type": "oauth", "access": "...", "refresh": "", "expires": 9007199254740991},
     "openai": {"type": "api_key", "key": "..."}}

Guarantees (see docs/login-roadmap.md, D2):

- The file is created with mode 0600 on POSIX, inside a 0700 directory.
- Writes are atomic: a temporary file in the same directory is fsynced and
  then moved over the target with os.replace. A failed write leaves the
  previous file intact.
- A corrupt file is never overwritten. Reading it raises CredentialStoreError,
  so a damaged file cannot silently erase stored keys.
- Writing a provider replaces its entry. Repeated logins do not add entries.
- `modify` is the only write path, so a read-modify-write cannot interleave.
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

    def read(self, provider):
        """Return the stored credential for a provider, or None."""
        with self._lock:
            return self._load().get(provider)

    def list(self):
        """Provider names with stored credentials. Never returns secrets."""
        with self._lock:
            return sorted(self._load())

    def modify(self, provider, fn):
        """Read-modify-write one provider under the lock.

        fn receives the current credential (or None) and returns the new one,
        or None to remove the entry. Returns the credential that is stored
        afterwards. If fn raises, nothing is written.
        """
        with self._lock:
            data = self._load()
            updated = fn(data.get(provider))
            if updated is None:
                data.pop(provider, None)
            else:
                data[provider] = updated
            self._save(data)
            return updated

    def delete(self, provider):
        """Remove a provider credential. Missing entries are ignored."""
        self.modify(provider, lambda current: None)


def env_name_for_provider(provider):
    """OpenRouter -> OPENROUTER_API_KEY, the variable aider already reads."""
    return f"{provider.upper()}_API_KEY"
