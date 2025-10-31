from .udiff_prompts import UnifiedDiffPrompts


class UnifiedDiffSimplePrompts(UnifiedDiffPrompts):
    """
    Prompts for the UnifiedDiffSimpleCoder.
    Inherits from UnifiedDiffPrompts and can override specific prompts
    if a simpler wording is desired for this edit format.
    """

    example_messages = []

    system_reminder = """# File editing rules:

Return edits similar to unified diffs that `diff -U0` would produce.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.

To make a new file, show a diff from `--- /dev/null` to `+++ path/to/new/file.ext`.

{final_reminders}
"""  # noqa
