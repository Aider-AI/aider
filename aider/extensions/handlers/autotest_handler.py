from ..handler import MutableContextHandler


class AutoTestHandler(MutableContextHandler):
    """
    A handler that runs tests automatically after code changes.
    """

    handler_name = "autotest"
    entrypoints = ["post"]

    def __init__(self, main_coder, **kwargs):
        """
        Initialize the AutoTestHandler.

        :param main_coder: The main coder instance.
        """
        self.main_coder = main_coder
        self.test_cmd = kwargs.get("test_cmd")

    def handle(self, messages) -> bool:
        """
        Runs tests automatically after code changes.

        :param messages: The current list of messages in the chat.
        :return: True if a reflection message was set, False otherwise.
        """
        if not self.test_cmd:
            return False

        if not self.main_coder.aider_edited_files:
            return False

        test_errors = self.main_coder.commands.cmd_test(self.test_cmd)
        self.main_coder.test_outcome = not test_errors
        if test_errors:
            ok = self.main_coder.io.confirm_ask("Attempt to fix test errors?")
            if ok:
                self.main_coder.reflected_message = test_errors
                return True

        return False
