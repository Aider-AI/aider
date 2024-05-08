class CoderPrompts:
    files_content_gpt_edits = "I committed the changes with git hash {hash} & commit msg: {message}"

    files_content_gpt_edits_no_repo = "I updated the files."

    files_content_gpt_no_edits = "I didn't see any properly formatted edits in your reply?!"

    files_content_local_edits = "I edited the files myself."

    lazy_prompt = """You are diligent and tireless!
You NEVER leave comments describing code without implementing it!
You always COMPLETELY IMPLEMENT the needed code!
"""

    example_messages = []

    files_content_prefix = (
        "I have *added these files to the chat* so you can go ahead and edit them:\n"
    )

    files_no_full_files = "I am not sharing any files that you can edit yet."

    repo_content_prefix = """I'm discussing files that are part of a git repository.
Here are summaries of some files present in my git repo.
Do not propose changes to these files, treat them as *read-only*.
If you need to edit one of them, ask me to *add it to the chat* first.
"""
