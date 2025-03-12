history_prompt = """
Update the history with changes shown in the diffs.
Describe actual user-facing changes, not every single commit that was made implementing them.

Only add new items not already listed.
Do NOT edit or update existing history entries.
Do NOT add duplicate entries for changes that have existing history entries.

Don't add entries for changes which may have been later undone, removed or superseded.

End each bullet with a period.

If the change was made by someone other than Paul Gauthier note it at the end of the bullet point as ", by XXX."

Be sure to attribute changes to the proper .x version.
Changes in the .x-dev version should be listed under a "### main branch" heading

Start a new "### main branch" section at the top of the file if needed.

Also, add this as the last bullet under the "### main branch" section:
{aider_line}
"""  # noqa
