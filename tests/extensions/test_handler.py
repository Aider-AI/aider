from aider.extensions.handler import ImmutableContextHandler, MutableContextHandler


class MockMutableHandler(MutableContextHandler):
    @property
    def entrypoints(self):
        return ["pre"]

    def handle(self, messages):
        messages.append("new message")
        return True


class MockImmutableHandler(ImmutableContextHandler):
    @property
    def entrypoints(self):
        return ["post"]

    def _handle(self, messages):
        # This handler inspects but doesn't modify messages
        pass


def test_mutable_context_handler():
    handler = MockMutableHandler()
    messages = ["original message"]

    modified = handler.handle(messages)

    assert modified is True
    assert messages == ["original message", "new message"]
    assert handler.entrypoints == ["pre"]


def test_immutable_context_handler():
    handler = MockImmutableHandler()
    messages = ["original message"]

    modified = handler.handle(messages)

    assert modified is False
    assert messages == ["original message"]
    assert handler.entrypoints == ["post"]
