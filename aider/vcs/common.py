from aider import prompts
from aider.waiting import WaitingSpinner


def get_commit_message(io, models, commit_prompt, diffs, context, user_language=None):
    diffs = "# Diffs:\n" + diffs

    content = ""
    if context:
        content += context + "\n"
    content += diffs

    system_content = commit_prompt or prompts.commit_system

    language_instruction = ""
    if user_language:
        language_instruction = f"\n- Is written in {user_language}."
    system_content = system_content.format(language_instruction=language_instruction)

    commit_message = None
    for model in models:
        spinner_text = f"Generating commit message with {model.name}"
        with WaitingSpinner(spinner_text):
            if model.system_prompt_prefix:
                current_system_content = model.system_prompt_prefix + "\n" + system_content
            else:
                current_system_content = system_content

            messages = [
                dict(role="system", content=current_system_content),
                dict(role="user", content=content),
            ]

            num_tokens = model.token_count(messages)
            max_tokens = model.info.get("max_input_tokens") or 0

            if max_tokens and num_tokens > max_tokens:
                continue

            commit_message = model.simple_send_with_retries(messages)
            if commit_message:
                break

    if not commit_message:
        io.tool_error("Failed to generate commit message!")
        return

    commit_message = commit_message.strip()
    if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
        commit_message = commit_message[1:-1].strip()

    return commit_message
