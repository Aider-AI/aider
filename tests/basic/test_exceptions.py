from unittest.mock import patch

import pytest

from aider.exceptions import ExInfo, LiteLLMExceptions


def test_litellm_exceptions_load():
    """Test that LiteLLMExceptions loads without errors"""
    ex = LiteLLMExceptions()
    assert len(ex.exceptions) > 0


def test_exceptions_tuple():
    """Test that exceptions_tuple returns a non-empty tuple"""
    ex = LiteLLMExceptions()
    assert isinstance(ex.exceptions_tuple(), tuple)
    assert len(ex.exceptions_tuple()) > 0


def test_get_ex_info():
    """Test get_ex_info returns correct ExInfo"""
    ex = LiteLLMExceptions()

    # Test with a known exception type
    from litellm import AuthenticationError

    auth_error = AuthenticationError(
        message="Invalid API key", llm_provider="openai", model="gpt-4"
    )
    ex_info = ex.get_ex_info(auth_error)
    assert isinstance(ex_info, ExInfo)
    assert ex_info.name == "AuthenticationError"
    assert ex_info.retry is False
    assert "API key" in ex_info.description

    # Test with unknown exception type
    class UnknownError(Exception):
        pass

    unknown = UnknownError()
    ex_info = ex.get_ex_info(unknown)
    assert isinstance(ex_info, ExInfo)
    assert ex_info.name is None
    assert ex_info.retry is None
    assert ex_info.description is None


def test_rate_limit_error():
    """Test specific handling of RateLimitError"""
    ex = LiteLLMExceptions()
    from litellm import RateLimitError

    rate_error = RateLimitError(message="Rate limit exceeded", llm_provider="openai", model="gpt-4")
    ex_info = ex.get_ex_info(rate_error)
    assert ex_info.retry is True
    assert "rate limited" in ex_info.description.lower()


def test_context_window_error():
    """Test specific handling of ContextWindowExceededError"""
    ex = LiteLLMExceptions()
    from litellm import ContextWindowExceededError

    ctx_error = ContextWindowExceededError(
        message="Context length exceeded", model="gpt-4", llm_provider="openai"
    )
    ex_info = ex.get_ex_info(ctx_error)
    assert ex_info.retry is False


def test_openrouter_error():
    """Test specific handling of OpenRouter API errors"""
    ex = LiteLLMExceptions()
    from litellm import APIConnectionError

    # Create an APIConnectionError with OpenrouterException message
    openrouter_error = APIConnectionError(
        message="APIConnectionError: OpenrouterException - 'choices'",
        model="openrouter/model",
        llm_provider="openrouter",
    )

    ex_info = ex.get_ex_info(openrouter_error)
    assert ex_info.retry is True
    assert "OpenRouter" in ex_info.description
    assert "overloaded" in ex_info.description
    assert "rate" in ex_info.description


def test_missing_litellm_exception_skipped():
    """Test that _load() skips exceptions not present in litellm (non-strict mode)"""
    import litellm

    original = getattr(litellm, "BadGatewayError", None)
    with patch.object(litellm, "BadGatewayError", create=False):
        delattr(litellm, "BadGatewayError")
        try:
            # Use a fresh instance with its own exceptions dict
            lex = LiteLLMExceptions.__new__(LiteLLMExceptions)
            lex.exceptions = dict()
            lex._load()

            # Should initialize without error
            assert len(lex.exceptions) > 0

            # exceptions_tuple should return a valid tuple without BadGatewayError
            tup = lex.exceptions_tuple()
            assert isinstance(tup, tuple)
            assert len(tup) > 0

            # BadGatewayError's class should not be in the exceptions dict
            for cls in tup:
                assert cls.__name__ != "BadGatewayError"

            # get_ex_info should return default ExInfo for unknown exception
            class FakeError(Exception):
                pass

            info = lex.get_ex_info(FakeError())
            assert info.name is None
            assert info.retry is None
            assert info.description is None
        finally:
            if original is not None:
                litellm.BadGatewayError = original


def test_strict_mode_raises_for_missing_exception():
    """Test that _load(strict=True) raises ValueError for missing litellm exceptions"""
    import litellm

    original = getattr(litellm, "BadGatewayError", None)
    with patch.object(litellm, "BadGatewayError", create=False):
        delattr(litellm, "BadGatewayError")
        try:
            lex = LiteLLMExceptions.__new__(LiteLLMExceptions)
            lex.exceptions = dict()
            with pytest.raises(ValueError, match="not found in litellm"):
                lex._load(strict=True)
        finally:
            if original is not None:
                litellm.BadGatewayError = original


def test_strict_mode_raises_for_unknown_litellm_exception():
    """Test that _load(strict=True) raises when litellm has an Error not in EXCEPTIONS"""
    import litellm

    # Add a fake exception class to litellm
    class FakeNewError(BaseException):
        pass

    litellm.FakeNewError = FakeNewError
    try:
        lex = LiteLLMExceptions.__new__(LiteLLMExceptions)
        lex.exceptions = dict()
        with pytest.raises(ValueError, match="FakeNewError is in litellm"):
            lex._load(strict=True)
    finally:
        delattr(litellm, "FakeNewError")
