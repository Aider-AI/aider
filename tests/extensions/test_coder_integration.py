from aider.coders.base_coder import Coder
from aider.coders.chat_chunks import ChatChunks
from aider.extensions.handler import Handler
from aider.extensions.handler_manager import HandlerManager


class MockHandler(Handler):
    def __init__(self, main_coder, entrypoint, call_recorder):
        self.main_coder = main_coder
        self._entrypoints = [entrypoint]
        self.call_recorder = call_recorder

    @property
    def entrypoints(self):
        return self._entrypoints

    def handle(self, messages):
        self.call_recorder.append(self._entrypoints[0])
        # This mock handler is immutable for simplicity.
        return False


class MockCoder(Coder):
    def __init__(self):
        self.cur_messages = []
        self.handler_manager = None

    def format_messages(self):
        chunks = ChatChunks()
        # This is a simplification. The real format_messages builds from many sources.
        # But for this test, just using cur_messages is sufficient.
        chunks.cur = self.cur_messages
        return chunks

    def send_message(self, inp):
        # This is a simplified version of the real Coder.send_message,
        # focusing only on the handler execution logic.
        self.cur_messages.append(dict(role="user", content=inp))

        chunks = self.format_messages()
        messages = chunks.all_messages()

        if self.handler_manager:
            self.handler_manager.run(messages, "pre")
            # The original coder refetches messages in case a mutable handler modified state
            chunks = self.format_messages()
            messages = chunks.all_messages()

        # Simulate an LLM response being added to the conversation
        self.cur_messages.append(dict(role="assistant", content="mock response"))

        if self.handler_manager:
            chunks = self.format_messages()
            messages = chunks.all_messages()
            self.handler_manager.run(messages, "post")


def test_pre_and_post_handlers_are_called_in_order():
    """
    Verify that handlers for 'pre' and 'post' entrypoints are called in the correct
    order during the message sending lifecycle.
    """
    call_recorder = []
    coder = MockCoder()

    pre_handler = MockHandler(main_coder=coder, entrypoint="pre", call_recorder=call_recorder)
    post_handler = MockHandler(main_coder=coder, entrypoint="post", call_recorder=call_recorder)

    # Manually set up the handler manager and its handlers
    coder.handler_manager = HandlerManager(coder, handlers=None)
    coder.handler_manager.handlers = [pre_handler, post_handler]

    coder.send_message("a user message")

    assert call_recorder == ["pre", "post"]
