from dataclasses import dataclass

from aider.dump import dump  # noqa: F401


@dataclass
class ExInfo:
    name: str
    retry: bool
    description: str


EXCEPTIONS = [
    ExInfo("APIConnectionError", True, None),
    ExInfo("APIError", True, None),
    ExInfo("APIResponseValidationError", True, None),
    ExInfo(
        "AuthenticationError",
        False,
        "The API provider is not able to authenticate you. Check your API key.",
    ),
    ExInfo("AzureOpenAIError", True, None),
    ExInfo("BadRequestError", False, None),
    ExInfo("BudgetExceededError", True, None),
    ExInfo(
        "ContentPolicyViolationError",
        True,
        "The API provider has refused the request due to a safety policy about the content.",
    ),
    ExInfo("ContextWindowExceededError", False, None),  # special case handled in base_coder
    ExInfo("InternalServerError", True, "The API provider's servers are down or overloaded."),
    ExInfo("InvalidRequestError", True, None),
    ExInfo("JSONSchemaValidationError", True, None),
    ExInfo("NotFoundError", False, None),
    ExInfo("OpenAIError", True, None),
    ExInfo(
        "RateLimitError",
        True,
        "The API provider has rate limited you. Try again later or check your quotas.",
    ),
    ExInfo("RouterRateLimitError", True, None),
    ExInfo("ServiceUnavailableError", True, "The API provider's servers are down or overloaded."),
    ExInfo("UnprocessableEntityError", True, None),
    ExInfo("UnsupportedParamsError", True, None),
    ExInfo(
        "Timeout",
        True,
        "The API provider timed out without returning a response. They may be down or overloaded.",
    ),
]


class LiteLLMExceptions:
    exceptions = dict()
    exception_info = {exi.name: exi for exi in EXCEPTIONS}

    def __init__(self):
        self._load()

    def _load(self, strict=False):
        import litellm

        for var in dir(litellm):
            if var.endswith("Error"):
                if var not in self.exception_info:
                    raise ValueError(f"{var} is in litellm but not in aider's exceptions list")

        for var in self.exception_info:
            ex = getattr(litellm, var)
            self.exceptions[ex] = self.exception_info[var]

    def exceptions_tuple(self):
        return tuple(self.exceptions)

    def get_ex_info(self, ex):
        """Return the ExInfo for a given exception instance"""
        import litellm

        if ex.__class__ is litellm.APIConnectionError:
            if "google.auth" in str(ex):
                return ExInfo(
                    "APIConnectionError", False, "You need to: pip install google-generativeai"
                )
            if "boto3" in str(ex):
                return ExInfo("APIConnectionError", False, "You need to: pip install boto3")
        return self.exceptions.get(ex.__class__, ExInfo(None, None, None))
