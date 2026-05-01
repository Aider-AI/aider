import asyncio
import logging
from collections.abc import AsyncIterator

from aider.providers.base import BaseProvider, ProviderEvent

logger = logging.getLogger(__name__)


def _is_rate_limit(exc: Exception) -> bool:
    try:
        import litellm

        if isinstance(exc, (litellm.RateLimitError, litellm.RouterRateLimitError)):
            return True
    except (ImportError, AttributeError):
        pass
    return "RateLimit" in type(exc).__name__ or "rate_limit" in str(exc).lower()


class AiderProvider(BaseProvider):
    """Wraps aider's Coder as a relay provider.

    Enables any litellm-supported model (GPT-4o, Gemini, Ollama) as a relay
    provider — primarily as an unlimited local fallback via Ollama when both
    CLI providers are exhausted (KB-2026-029).
    """

    tier = "completion_api"

    def __init__(self, model: str, fnames: list | None = None, **coder_kwargs):
        self._model_name = model
        self._fnames = fnames or []
        self._coder_kwargs = coder_kwargs
        self._coder = None

    def _get_coder(self):
        if self._coder is None:
            from aider.coders import Coder
            from aider.io import InputOutput
            from aider.models import Model

            io = InputOutput(pretty=False, yes=True)
            model = Model(self._model_name)
            self._coder = Coder.create(
                main_model=model,
                io=io,
                fnames=self._fnames,
                auto_commits=True,
                **self._coder_kwargs,
            )
        return self._coder

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        coder = self._get_coder()
        try:
            response = await asyncio.to_thread(coder.run, with_message=prompt)
            yield ProviderEvent(type="text", content=response or "")
            yield ProviderEvent(type="done", session_id=None)
        except Exception as exc:
            if _is_rate_limit(exc):
                logger.warning("AiderProvider rate limit: %s", exc)
                yield ProviderEvent(type="exhausted")
            else:
                logger.error("AiderProvider error: %s", exc)
                yield ProviderEvent(type="error", content=str(exc))

    @property
    def current_session_id(self) -> str | None:
        return None
