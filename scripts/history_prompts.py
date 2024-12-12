history_prompt = """
Update the history with changes shown in the diffs.
Describe actual user-facing changes, not every single commit that was made implementing them.

Only add new items not already listed.
Do NOT edit or update existing history entries.
Do NOT add duplicate entries for changes that have existing history entries.

End each bullet with a period.

Be sure to attribute changes to the proper .x version.
Changes in the .x-dev version should be listed under a "### main branch" heading

Also, add this as the last bullet under the "### main branch" section:
{aider_line}
"""  # noqa
