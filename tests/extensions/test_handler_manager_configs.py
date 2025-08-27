from unittest.mock import call, patch

from aider.extensions.handler import MutableContextHandler
from aider.extensions.handler_manager import HandlerManager


# A mock handler class that can be discovered by the manager
class MockHandlerForLoading(MutableContextHandler):
    def __init__(self, main_coder, **config):
        self.main_coder = main_coder
        self.config = config

    @property
    def entrypoints(self):
        return ["pre"]

    def handle(self, messages):
        return False


class MockIO:
    def __init__(self):
        self.warnings = []

    def tool_warning(self, message):
        self.warnings.append(message)


class MockCoder:
    def __init__(self):
        self.io = MockIO()


class MockModule:
    pass


@patch("importlib.import_module")
def test_load_handlers_with_valid_configs(mock_import_module):
    """
    Test that handlers are loaded correctly from string and dict configurations.
    """
    mock_module = MockModule()
    mock_module.SomeHandlerClass = MockHandlerForLoading
    mock_import_module.return_value = mock_module

    coder = MockCoder()
    handlers_config = [
        "mock-handler",
        {"name": "mock-handler", "config": {"key": "value"}},
    ]

    manager = HandlerManager(coder, handlers=handlers_config)

    assert len(manager.handlers) == 2
    assert isinstance(manager.handlers[0], MockHandlerForLoading)
    assert manager.handlers[0].config == {}
    assert isinstance(manager.handlers[1], MockHandlerForLoading)
    assert manager.handlers[1].config == {"key": "value"}
    assert not coder.io.warnings

    expected_module_path = "aider.extensions.handlers.mock_handler_handler"
    mock_import_module.assert_has_calls([call(expected_module_path), call(expected_module_path)])


@patch("importlib.import_module")
def test_load_handlers_with_invalid_configs(mock_import_module):
    """
    Test that malformed handler configurations are skipped and warnings are logged.
    """
    coder = MockCoder()
    handlers_config = [
        {"config": {"key": "value"}},  # Missing 'name'
        123,  # Invalid type
    ]

    manager = HandlerManager(coder, handlers=handlers_config)

    assert len(manager.handlers) == 0
    assert len(coder.io.warnings) == 2
    assert "Handler configuration missing name" in coder.io.warnings[0]
    assert "Invalid handler configuration" in coder.io.warnings[1]
