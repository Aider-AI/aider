# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from .threads import (
    Threads,
    AsyncThreads,
    ThreadsWithRawResponse,
    AsyncThreadsWithRawResponse,
    ThreadsWithStreamingResponse,
    AsyncThreadsWithStreamingResponse,
)
from ..._compat import cached_property
from .chat.chat import Chat, AsyncChat
from .assistants import (
    Assistants,
    AsyncAssistants,
    AssistantsWithRawResponse,
    AsyncAssistantsWithRawResponse,
    AssistantsWithStreamingResponse,
    AsyncAssistantsWithStreamingResponse,
)
from ..._resource import SyncAPIResource, AsyncAPIResource
from .vector_stores import (
    VectorStores,
    AsyncVectorStores,
    VectorStoresWithRawResponse,
    AsyncVectorStoresWithRawResponse,
    VectorStoresWithStreamingResponse,
    AsyncVectorStoresWithStreamingResponse,
)
from .threads.threads import Threads, AsyncThreads
from .vector_stores.vector_stores import VectorStores, AsyncVectorStores

__all__ = ["Beta", "AsyncBeta"]


class Beta(SyncAPIResource):
    @cached_property
    def chat(self) -> Chat:
        return Chat(self._client)

    @cached_property
    def vector_stores(self) -> VectorStores:
        return VectorStores(self._client)

    @cached_property
    def assistants(self) -> Assistants:
        return Assistants(self._client)

    @cached_property
    def threads(self) -> Threads:
        return Threads(self._client)

    @cached_property
    def with_raw_response(self) -> BetaWithRawResponse:
        return BetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BetaWithStreamingResponse:
        return BetaWithStreamingResponse(self)


class AsyncBeta(AsyncAPIResource):
    @cached_property
    def chat(self) -> AsyncChat:
        return AsyncChat(self._client)

    @cached_property
    def vector_stores(self) -> AsyncVectorStores:
        return AsyncVectorStores(self._client)

    @cached_property
    def assistants(self) -> AsyncAssistants:
        return AsyncAssistants(self._client)

    @cached_property
    def threads(self) -> AsyncThreads:
        return AsyncThreads(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncBetaWithRawResponse:
        return AsyncBetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBetaWithStreamingResponse:
        return AsyncBetaWithStreamingResponse(self)


class BetaWithRawResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def vector_stores(self) -> VectorStoresWithRawResponse:
        return VectorStoresWithRawResponse(self._beta.vector_stores)

    @cached_property
    def assistants(self) -> AssistantsWithRawResponse:
        return AssistantsWithRawResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> ThreadsWithRawResponse:
        return ThreadsWithRawResponse(self._beta.threads)


class AsyncBetaWithRawResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def vector_stores(self) -> AsyncVectorStoresWithRawResponse:
        return AsyncVectorStoresWithRawResponse(self._beta.vector_stores)

    @cached_property
    def assistants(self) -> AsyncAssistantsWithRawResponse:
        return AsyncAssistantsWithRawResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> AsyncThreadsWithRawResponse:
        return AsyncThreadsWithRawResponse(self._beta.threads)


class BetaWithStreamingResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def vector_stores(self) -> VectorStoresWithStreamingResponse:
        return VectorStoresWithStreamingResponse(self._beta.vector_stores)

    @cached_property
    def assistants(self) -> AssistantsWithStreamingResponse:
        return AssistantsWithStreamingResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> ThreadsWithStreamingResponse:
        return ThreadsWithStreamingResponse(self._beta.threads)


class AsyncBetaWithStreamingResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def vector_stores(self) -> AsyncVectorStoresWithStreamingResponse:
        return AsyncVectorStoresWithStreamingResponse(self._beta.vector_stores)

    @cached_property
    def assistants(self) -> AsyncAssistantsWithStreamingResponse:
        return AsyncAssistantsWithStreamingResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> AsyncThreadsWithStreamingResponse:
        return AsyncThreadsWithStreamingResponse(self._beta.threads)
