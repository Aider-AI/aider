

def retry_exceptions():
    import httpx
    import openai

    return (
        # httpx
        httpx.ConnectError,
        httpx.RemoteProtocolError,
        httpx.ReadTimeout,
        #
        # litellm exceptions inherit from openai exceptions
        # https://docs.litellm.ai/docs/exception_mapping
        #
        # openai.BadRequestError,
        # litellm.ContextWindowExceededError,
        # litellm.ContentPolicyViolationError,
        #
        # openai.AuthenticationError,
        # openai.PermissionDeniedError,
        # openai.NotFoundError,
        #
        openai.APITimeoutError,
        openai.UnprocessableEntityError,
        openai.RateLimitError,
        openai.APIConnectionError,
        # openai.APIError,
        # openai.APIStatusError,
        openai.InternalServerError,
    )


class LiteLLMExceptions:
