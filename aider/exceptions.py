from dataclasses import dataclass

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


@dataclass
class ExInfo:
    name: str
    retry: bool
    description: str

EXCEPTIONS = [
    ExInfo("APIConnectionError", True, None),
    ExInfo("APIError", True, None),
    ExInfo("APIResponseValidationError", True, None),
    ExInfo("AuthenticationError", True, None),
    ExInfo("AzureOpenAIError", True, None),
    ExInfo("BadRequestError", True, None),
    ExInfo("BudgetExceededError", True, None),
    ExInfo("ContentPolicyViolationError", True, None),
    ExInfo("ContextWindowExceededError", True, None),
    ExInfo("InternalServerError", True, None),
    ExInfo("InvalidRequestError", True, None),
    ExInfo("JSONSchemaValidationError", True, None),
    ExInfo("NotFoundError", True, None),
    ExInfo("OpenAIError", True, None),
    ExInfo("RateLimitError", True, None),
    ExInfo("RouterRateLimitError", True, None),
    ExInfo("ServiceUnavailableError", True, None),
    ExInfo("UnprocessableEntityError", True, None),
    ExInfo("UnsupportedParamsError", True, None),
]


class LiteLLMExceptions:
    exceptions = dict()

    def __init__(self):
        self._load()

    def _load(self, strict=False):
        import litellm

        for var in dir(litellm):
            if not var.endswith("Error"):
                continue

            ex_info = None
            for exi in EXCEPTIONS:
                if var == exi.name:
                    ex_info = exi
                    break

            if strict and not ex_info:
                raise ValueError(f"{var} is in litellm but not in aider's exceptions list")

            ex = getattr(litellm, var)
            self.exceptions[ex] = ex_info

    def exceptions_tuple(self):
        return tuple(self.exceptions)

    def get_ex_info(self, ex):
        """Return the ExInfo for a given exception instance"""
        return self.exceptions.get(ex.__class__)



litellm_ex = LiteLLMExceptions()
litellm_ex._load(strict=True)
