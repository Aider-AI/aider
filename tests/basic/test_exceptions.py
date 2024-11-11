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
