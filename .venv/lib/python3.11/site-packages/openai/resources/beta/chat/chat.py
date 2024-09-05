# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from ...._compat import cached_property
from .completions import Completions, AsyncCompletions
from ...._resource import SyncAPIResource, AsyncAPIResource

__all__ = ["Chat", "AsyncChat"]


class Chat(SyncAPIResource):
    @cached_property
    def completions(self) -> Completions:
        return Completions(self._client)


class AsyncChat(AsyncAPIResource):
    @cached_property
    def completions(self) -> AsyncCompletions:
        return AsyncCompletions(self._client)
