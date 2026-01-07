from .agent_prompts import AgentPrompts
from .editblock_coder import EditBlockCoder


class AgentCoder(EditBlockCoder):
    """
    Autonomous agent that automatically edits files and runs tests.
    """

    edit_format = "agent"
    gpt_prompts = AgentPrompts()

    def __init__(self, *args, **kwargs):
        # Extract agent-specific kwargs before passing to super
        self.max_agent_iterations = kwargs.pop("max_agent_iterations", 3)

        # Force auto_test to be enabled for agent mode
        kwargs["auto_test"] = True

        super().__init__(*args, **kwargs)

        # Track iterations for agent mode
        self.agent_iteration_count = 0

    def send_message(self, inp):
        """
        Override to implement autonomous test-fix iterations without user confirmation.
        """
        # Call parent's send_message to handle LLM communication
        yield from super().send_message(inp)

        # Note: The parent's send_message handles:
        # 1. Sending message to LLM
        # 2. Calling reply_completed()
        # 3. Calling apply_updates()
        # 4. Auto-test section (lines 1616-1623 in base_coder.py)
        #
        # The auto_test section calls io.confirm_ask("Attempt to fix test errors?")
        # We override this behavior below by checking for reflected_message

    def run_one(self, user_message, preproc):
        """
        Override run_one to handle agent-specific iteration logic.

        Agent mode autonomously handles test failures by:
        1. Temporarily wrapping io.confirm_ask() to auto-confirm test-fix attempts
        2. Tracking iterations and enforcing max_agent_iterations limit
        3. Using the reflected_message mechanism to trigger fix iterations

        The base implementation's auto_test section (base_coder.py:1616-1623) calls
        io.confirm_ask("Attempt to fix test errors?"). By wrapping this method,
        we can automatically say "yes" in agent mode without modifying the base flow.
        """
        self.init_before_message()

        if preproc:
            message = self.preproc_user_input(user_message)
        else:
            message = user_message

        while message:
            self.reflected_message = None

            # For agent mode, auto-confirm test fix attempts (but not other confirmations)
            # We do this by temporarily wrapping confirm_ask
            original_confirm_ask = self.io.confirm_ask

            def agent_confirm_ask(question=None, subject=None, explicit_yes_required=False):
                """Wrapper that auto-confirms test-related questions in agent mode."""
                # Auto-confirm only test/fix-related questions
                if question and ("test" in question.lower() or "fix" in question.lower()):
                    # Check iteration limit
                    if self.agent_iteration_count >= self.max_agent_iterations:
                        self.io.tool_output(
                            f"\n[Agent Mode] Reached maximum iteration limit "
                            f"({self.max_agent_iterations})."
                        )
                        return False

                    self.agent_iteration_count += 1
                    self.io.tool_output(
                        f"\n[Agent Mode] Iteration {self.agent_iteration_count}/"
                        f"{self.max_agent_iterations}: Attempting automatic fix..."
                    )
                    return True

                # For other questions, use the original behavior
                return original_confirm_ask(question, subject, explicit_yes_required)

            try:
                # Temporarily replace confirm_ask for agent behavior
                self.io.confirm_ask = agent_confirm_ask

                # Run the standard message flow (which includes auto_test)
                list(self.send_message(message))

            finally:
                # Always restore original confirm_ask
                self.io.confirm_ask = original_confirm_ask

            if not self.reflected_message:
                break

            if self.num_reflections >= self.max_reflections:
                self.io.tool_warning(f"Only {self.max_reflections} reflections allowed, stopping.")
                return

            self.num_reflections += 1
            message = self.reflected_message

    def get_edits(self):
        """
        Override to add agent-specific logging.
        """
        edits = super().get_edits()

        if edits and self.verbose:
            self.io.tool_output(f"[Agent Mode] Found {len(edits)} edit(s) to apply")

        return edits
