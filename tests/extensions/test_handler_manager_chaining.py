from unittest.mock import MagicMock

from aider.extensions.handler import MutableContextHandler
from aider.extensions.handler_manager import HandlerManager


class MockCoderForChaining:
    def __init__(self):
        self.cur_messages = []

    def format_messages(self):
        """
        Simulates the coder re-formatting its message history.
        It includes its current messages plus a marker to show it was called.
        """
        chunks = MagicMock()
        all_msgs = self.cur_messages + [{"role": "system", "content": "refreshed"}]
        chunks.all_messages.return_value = all_msgs
        return chunks


class ChainingHandlerA(MutableContextHandler):
    """A mutable handler that modifies the coder's message history."""

    def __init__(self, main_coder):
        self.main_coder = main_coder

    @property
    def entrypoints(self):
        return ["pre"]

    def handle(self, messages):
        # A real handler must modify the coder's state for changes to persist.
        self.main_coder.cur_messages.append({"role": "user", "content": "message from A"})
        return True


class ChainingHandlerB(MutableContextHandler):
    """A handler that records the messages it receives for verification."""

    def __init__(self, main_coder):
        self.received_messages = None

    @property
    def entrypoints(self):
        return ["pre"]

    def handle(self, messages):
        self.received_messages = list(messages)
        return False


def test_handler_chaining_with_context_modification():
    """
    Verify that a handler receives the modified context from a preceding handler
    after the coder's state has been refreshed.
    """
    coder = MockCoderForChaining()
    manager = HandlerManager(coder, handlers=None)

    handler_a = ChainingHandlerA(coder)
    handler_b = ChainingHandlerB(coder)
    manager.handlers = [handler_a, handler_b]

    # This is the message list as it would be passed from Coder.send_message.
    initial_messages = [{"role": "user", "content": "original message"}]
    # The coder's internal state matches this at the start of the run.
    coder.cur_messages = initial_messages[:]

    manager.run(initial_messages, "pre")

    # HandlerA modifies coder.cur_messages and returns True.
    # The manager then calls coder.format_messages(), which returns an updated list.
    # HandlerB should receive this new list.
    expected_received = [
        {"role": "user", "content": "original message"},
        {"role": "user", "content": "message from A"},
        {"role": "system", "content": "refreshed"},
    ]
    assert handler_b.received_messages == expected_received
