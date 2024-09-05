"""Contains all custom errors."""

from requests import HTTPError


# HEADERS ERRORS


class LocalTokenNotFoundError(EnvironmentError):
    """Raised if local token is required but not found."""


# HTTP ERRORS


class OfflineModeIsEnabled(ConnectionError):
    """Raised when a request is made but `HF_HUB_OFFLINE=1` is set as environment variable."""


# INFERENCE CLIENT ERRORS


class InferenceTimeoutError(HTTPError, TimeoutError):
    """Error raised when a model is unavailable or the request times out."""


# INFERENCE ENDPOINT ERRORS


class InferenceEndpointError(Exception):
    """Generic exception when dealing with Inference Endpoints."""


class InferenceEndpointTimeoutError(InferenceEndpointError, TimeoutError):
    """Exception for timeouts while waiting for Inference Endpoint."""


# SAFETENSORS ERRORS


class SafetensorsParsingError(Exception):
    """Raised when failing to parse a safetensors file metadata.

    This can be the case if the file is not a safetensors file or does not respect the specification.
    """


class NotASafetensorsRepoError(Exception):
    """Raised when a repo is not a Safetensors repo i.e. doesn't have either a `model.safetensors` or a
    `model.safetensors.index.json` file.
    """


# TEMPLATING ERRORS


class TemplateError(Exception):
    """Any error raised while trying to fetch or render a chat template."""


# TEXT GENERATION ERRORS


class TextGenerationError(HTTPError):
    """Generic error raised if text-generation went wrong."""


# Text Generation Inference Errors
class ValidationError(TextGenerationError):
    """Server-side validation error."""


class GenerationError(TextGenerationError):
    pass


class OverloadedError(TextGenerationError):
    pass


class IncompleteGenerationError(TextGenerationError):
    pass


class UnknownError(TextGenerationError):
    pass


# VALIDATION ERRORS


class HFValidationError(ValueError):
    """Generic exception thrown by `huggingface_hub` validators.

    Inherits from [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError).
    """
