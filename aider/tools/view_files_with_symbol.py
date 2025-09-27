view_files_with_symbol_schema = {
    "type": "function",
    "function": {
        "name": "ViewFilesWithSymbol",
        "description": "View files that contain a specific symbol (e.g., class, function).",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The symbol to search for.",
                },
            },
            "required": ["symbol"],
        },
    },
}


def _execute_view_files_with_symbol(coder, symbol):
    """
    Find files containing a symbol using RepoMap and return them as text.
    Checks files already in context first.
    """
    if not coder.repo_map:
        coder.io.tool_output("⚠️ Repo map not available, cannot use ViewFilesWithSymbol tool.")
        return "Repo map not available"

    if not symbol:
        return "Error: Missing 'symbol' parameter for ViewFilesWithSymbol"

    # 1. Check files already in context
    files_in_context = list(coder.abs_fnames) + list(coder.abs_read_only_fnames)
    found_in_context = []
    for abs_fname in files_in_context:
        rel_fname = coder.get_rel_fname(abs_fname)
        try:
            # Use get_tags for consistency with RepoMap usage elsewhere for now.
            tags = coder.repo_map.get_tags(abs_fname, rel_fname)
            for tag in tags:
                if tag.name == symbol:
                    found_in_context.append(rel_fname)
                    break  # Found in this file, move to next
        except Exception as e:
            coder.io.tool_warning(
                f"Could not get symbols for {rel_fname} while checking context: {e}"
            )

    if found_in_context:
        # Symbol found in already loaded files. Report this and stop.
        file_list = ", ".join(sorted(list(set(found_in_context))))
        coder.io.tool_output(f"Symbol '{symbol}' found in already loaded file(s): {file_list}")
        return f"Symbol '{symbol}' found in already loaded file(s): {file_list}"

    # 2. If not found in context, search the repository using RepoMap
    coder.io.tool_output(f"🔎 Searching for symbol '{symbol}' in repository...")
    try:
        found_files = set()
        current_context_files = coder.abs_fnames | coder.abs_read_only_fnames
        files_to_search = set(coder.get_all_abs_files()) - current_context_files

        rel_fname_to_abs = {}
        all_tags = []

        for fname in files_to_search:
            rel_fname = coder.get_rel_fname(fname)
            rel_fname_to_abs[rel_fname] = fname
            try:
                tags = coder.repo_map.get_tags(fname, rel_fname)
                all_tags.extend(tags)
            except Exception as e:
                coder.io.tool_warning(f"Could not get tags for {rel_fname}: {e}")

        # Find matching symbols
        for tag in all_tags:
            if tag.name == symbol:
                # Use absolute path directly if available, otherwise resolve from relative path
                abs_fname = rel_fname_to_abs.get(tag.rel_fname) or coder.abs_root_path(tag.fname)
                if abs_fname in files_to_search:  # Ensure we only add files we intended to search
                    found_files.add(coder.get_rel_fname(abs_fname))

        # Return formatted text instead of adding to context
        if found_files:
            found_files_list = sorted(list(found_files))
            if len(found_files) > 10:
                result = (
                    f"Found symbol '{symbol}' in {len(found_files)} files:"
                    f" {', '.join(found_files_list[:10])} and {len(found_files) - 10} more"
                )
                coder.io.tool_output(f"🔎 Found '{symbol}' in {len(found_files)} files")
            else:
                result = (
                    f"Found symbol '{symbol}' in {len(found_files)} files:"
                    f" {', '.join(found_files_list)}"
                )
                coder.io.tool_output(
                    f"🔎 Found '{symbol}' in files:"
                    f" {', '.join(found_files_list[:5])}{' and more' if len(found_files) > 5 else ''}"
                )

            return result
        else:
            coder.io.tool_output(f"⚠️ Symbol '{symbol}' not found in searchable files")
            return f"Symbol '{symbol}' not found in searchable files"

    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesWithSymbol: {str(e)}")
        return f"Error: {str(e)}"
