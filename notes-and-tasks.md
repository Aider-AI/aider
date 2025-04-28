## LLM Status Indicator Implementation (2025-04-28)

**Goal:** Add a visual indicator (status message or spinner) to show the user when Aider is actively waiting for a response from the LLM API.

**Discussion Summary:**
*   Explored existing progress indicators (repo scan progress, response streaming, tool output, `Spinner` class).
*   Identified the need for an indicator specifically during the LLM wait time.
*   Traced the relevant call stack: `Coder.run` -> `Coder.send_message` -> `Coder.send` -> `Model.send_completion`.
*   Decided on an initial simple implementation using a static text message (`Waiting for LLM response...`) managed within `Coder.send` and `Coder.show_send_output_stream`.
*   Confirmed the approach works for both streaming (shows during initial lag) and non-streaming modes.
*   Discussed the necessity of `io.isatty()` checks to only show the dynamic message in interactive terminals.

**Code Changes Made:**
*   **File:** `aider/coders/base_coder.py`
    *   **`Coder.send` method:**
        *   Added code to print "Waiting for LLM response..." before the `litellm.completion` call (using `io.tool_output`, conditional on `io.isatty()`).
        *   Wrapped the `litellm.completion` call and stream handling in `try...except...finally` to ensure the status message is cleared (overwritten with spaces via `\r`) on successful completion (for non-streaming), error, or keyboard interrupt.
        *   Passed the status message string to `show_send_output_stream`.
    *   **`Coder.show_send_output_stream` method:**
        *   Added logic at the beginning of the stream iteration to check if a status message was active and clear it (overwrite with spaces via `\r`) upon receiving the *first* chunk containing content/tool_call/reasoning from the LLM.
        *   Ensured the status message is cleared in edge cases like `FinishReasonLength` exception or if the stream ends without content.

**Next Steps:**
1.  **Test:** Restart Aider (in the editable install environment) and send prompts to verify:
    *   The "Waiting for LLM response..." message appears immediately after sending a prompt.
    *   The message disappears as soon as the first token of the LLM response starts streaming.
    *   The message appears and disappears correctly for non-streaming calls (`--no-stream`).
    *   The message is cleared cleanly if an API error or KeyboardInterrupt occurs.
2.  **(Optional) Enhancement:** Replace the static text message with the animated `aider.utils.Spinner` class for a better user experience. This might require passing the `io` object further down or refactoring the spinner's usage.
3.  **(Optional) Unit Tests:** Add tests for the `Coder.send` method, mocking `io.tool_output` and the `litellm.completion` call, to assert that the status message is displayed and cleared at the correct times under various conditions (streaming, non-streaming, error, interrupt).
