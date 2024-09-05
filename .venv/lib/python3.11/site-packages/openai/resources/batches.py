# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Optional
from typing_extensions import Literal

import httpx

from .. import _legacy_response
from ..types import batch_list_params, batch_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import (
    maybe_transform,
    async_maybe_transform,
)
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..pagination import SyncCursorPage, AsyncCursorPage
from ..types.batch import Batch
from .._base_client import (
    AsyncPaginator,
    make_request_options,
)

__all__ = ["Batches", "AsyncBatches"]


class Batches(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> BatchesWithRawResponse:
        return BatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BatchesWithStreamingResponse:
        return BatchesWithStreamingResponse(self)

    def create(
        self,
        *,
        completion_window: Literal["24h"],
        endpoint: Literal["/v1/chat/completions", "/v1/embeddings", "/v1/completions"],
        input_file_id: str,
        metadata: Optional[Dict[str, str]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Creates and executes a batch from an uploaded file of requests

        Args:
          completion_window: The time frame within which the batch should be processed. Currently only `24h`
              is supported.

          endpoint: The endpoint to be used for all requests in the batch. Currently
              `/v1/chat/completions`, `/v1/embeddings`, and `/v1/completions` are supported.
              Note that `/v1/embeddings` batches are also restricted to a maximum of 50,000
              embedding inputs across all requests in the batch.

          input_file_id: The ID of an uploaded file that contains requests for the new batch.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your input file must be formatted as a
              [JSONL file](https://platform.openai.com/docs/api-reference/batch/request-input),
              and must be uploaded with the purpose `batch`. The file can contain up to 50,000
              requests, and can be up to 100 MB in size.

          metadata: Optional custom metadata for the batch.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/batches",
            body=maybe_transform(
                {
                    "completion_window": completion_window,
                    "endpoint": endpoint,
                    "input_file_id": input_file_id,
                    "metadata": metadata,
                },
                batch_create_params.BatchCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def retrieve(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Retrieves a batch.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return self._get(
            f"/batches/{batch_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[Batch]:
        """List your organization's batches.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/batches",
            page=SyncCursorPage[Batch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=Batch,
        )

    def cancel(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """Cancels an in-progress batch.

        The batch will be in status `cancelling` for up to
        10 minutes, before changing to `cancelled`, where it will have partial results
        (if any) available in the output file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return self._post(
            f"/batches/{batch_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )


class AsyncBatches(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncBatchesWithRawResponse:
        return AsyncBatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBatchesWithStreamingResponse:
        return AsyncBatchesWithStreamingResponse(self)

    async def create(
        self,
        *,
        completion_window: Literal["24h"],
        endpoint: Literal["/v1/chat/completions", "/v1/embeddings", "/v1/completions"],
        input_file_id: str,
        metadata: Optional[Dict[str, str]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Creates and executes a batch from an uploaded file of requests

        Args:
          completion_window: The time frame within which the batch should be processed. Currently only `24h`
              is supported.

          endpoint: The endpoint to be used for all requests in the batch. Currently
              `/v1/chat/completions`, `/v1/embeddings`, and `/v1/completions` are supported.
              Note that `/v1/embeddings` batches are also restricted to a maximum of 50,000
              embedding inputs across all requests in the batch.

          input_file_id: The ID of an uploaded file that contains requests for the new batch.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your input file must be formatted as a
              [JSONL file](https://platform.openai.com/docs/api-reference/batch/request-input),
              and must be uploaded with the purpose `batch`. The file can contain up to 50,000
              requests, and can be up to 100 MB in size.

          metadata: Optional custom metadata for the batch.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/batches",
            body=await async_maybe_transform(
                {
                    "completion_window": completion_window,
                    "endpoint": endpoint,
                    "input_file_id": input_file_id,
                    "metadata": metadata,
                },
                batch_create_params.BatchCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    async def retrieve(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Retrieves a batch.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return await self._get(
            f"/batches/{batch_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Batch, AsyncCursorPage[Batch]]:
        """List your organization's batches.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/batches",
            page=AsyncCursorPage[Batch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=Batch,
        )

    async def cancel(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """Cancels an in-progress batch.

        The batch will be in status `cancelling` for up to
        10 minutes, before changing to `cancelled`, where it will have partial results
        (if any) available in the output file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return await self._post(
            f"/batches/{batch_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )


class BatchesWithRawResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = _legacy_response.to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithRawResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = _legacy_response.async_to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            batches.cancel,
        )


class BatchesWithStreamingResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = to_streamed_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithStreamingResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = async_to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = async_to_streamed_response_wrapper(
            batches.cancel,
        )
