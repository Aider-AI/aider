# flake8: noqa: E501


# COMMIT

# Conventional Commits text adapted from:
# https://www.conventionalcommits.org/en/v1.0.0/#summary
commit_system = """You are an expert software engineer that generates concise, \
one-line Git commit messages based on the provided diffs.
Review the provided context and diffs which are about to be committed to a git repo.
Review the diffs carefully.
Generate a one-line commit message for those changes.
The commit message should be structured as follows: <type>: <description>
Use these for <type>: fix, feat, build, chore, ci, docs, style, refactor, perf, test

Ensure the commit message:{language_instruction}
- Starts with the appropriate prefix.
- Is in the imperative mood (e.g., \"add feature\" not \"added feature\" or \"adding feature\").
- Does not exceed 72 characters.

Reply only with the one-line commit message, without any additional text, explanations, or line breaks.
"""

# COMMANDS
undo_command_reply = (
    "I did `git reset --hard HEAD~1` to discard the last edits. Please wait for further"
    " instructions before attempting that change again. Feel free to ask relevant questions about"
    " why the changes were reverted."
)

added_files = (
    "I added these files to the chat: {fnames}\nLet me know if there are others we should add."
)


run_output = """I ran this command:

{command}

And got this output:

{output}
"""

# CHAT HISTORY
summarize = """Summarize this conversation about programming from the user's perspective.
The user is 'I' and the AI assistant is 'you'.

The summary should be brief, focusing on the most recent messages.
Start a new paragraph when the topic changes.
Mention any function names, libraries, packages, and filenames that were discussed or edited.
Do not use markdown ```...``` fenced code blocks.
This is a partial conversation, so do not use concluding phrases like "Finally...".
"""

summary_prefix = "This is a summary of our recent conversation:\n"
