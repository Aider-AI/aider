from abc import ABC, abstractmethod


class Handler(ABC):
    """
    Base class for extension handlers.
    """

    @property
    @abstractmethod
    def entrypoints(self) -> list[str]:
        """
        The entrypoints at which this handler should be run.
        e.g., ["pre", "post"]
        """
        pass

    @abstractmethod
    def handle(self, messages) -> bool:
        """
        Handle the given messages.
        Return True if context was modified, False otherwise.
        """
        pass



class MutableContextHandler(Handler):
    """
    A handler that can modify the chat context.
    """

    @abstractmethod
    def handle(self, messages) -> bool:
        """
        Handle the messages and return True if context was modified.
        """
        pass


class ImmutableContextHandler(Handler):
    """
    A handler that can inspect the context but not modify it.
    """

    def handle(self, messages) -> bool:
        """
        Handle the messages and return False, as context is not modified.
        """
        self._handle(messages)
        return False

    @abstractmethod
    def _handle(self, messages):
        """
        Process the messages.
        """
        pass
