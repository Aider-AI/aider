# flake8: noqa: E501


# COMMIT
commit_system = """You are an expert software engineer.
Review the provided context and diffs which are about to be committed to a git repo.
Generate a *SHORT* 1 line, 1 sentence commit message that describes the purpose of the changes.
The commit message MUST be in the past tense.
It must describe the changes *which have been made* in the diffs!
Reply with JUST the commit message, without quotes, comments, questions, etc!
"""

# COMMANDS
undo_command_reply = "I did `git reset --hard HEAD~1` to discard the last edits."

added_files = "I added these *read-write* files: {fnames}"


run_output = """I ran this command:

{command}

And got this output:

{output}
"""
