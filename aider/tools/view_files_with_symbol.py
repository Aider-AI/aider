import os

def _execute_view_files_with_symbol(coder, symbol):
    """
    Find files containing a symbol using RepoMap and add them to context.
    Checks files already in context first.
    """
    if not coder.repo_map:
        coder.io.tool_output("⚠️ Repo map not available, cannot use ViewFilesWithSymbol tool.")
        return "Repo map not available"

    if not symbol:
        return "Error: Missing 'symbol' parameter for ViewFilesWithSymbol"

    # --- Start Modification ---
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
                    break # Found in this file, move to next
        except Exception as e:
            coder.io.tool_warning(f"Could not get symbols for {rel_fname} while checking context: {e}")

    if found_in_context:
        # Symbol found in already loaded files. Report this and stop.
        file_list = ", ".join(sorted(list(set(found_in_context))))
        coder.io.tool_output(f"Symbol '{symbol}' found in already loaded file(s): {file_list}. No external search performed.")
        return f"Symbol '{symbol}' found in already loaded file(s): {file_list}. No external search performed."
    # --- End Modification ---


    # 2. If not found in context, search the repository using RepoMap
    coder.io.tool_output(f"🔎 Searching for symbol '{symbol}' in repository (excluding current context)...")
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
                if abs_fname in files_to_search: # Ensure we only add files we intended to search
                    found_files.add(abs_fname)

        # Limit the number of files added
        if len(found_files) > coder.max_files_per_glob:
             coder.io.tool_output(
                f"⚠️ Found symbol '{symbol}' in {len(found_files)} files, "
                f"limiting to {coder.max_files_per_glob} most relevant files."
            )
             # Sort by modification time (most recent first) - approximate relevance
             sorted_found_files = sorted(list(found_files), key=lambda f: os.path.getmtime(f), reverse=True)
             found_files = set(sorted_found_files[:coder.max_files_per_glob])

        # Add files to context (as read-only)
        added_count = 0
        added_files_rel = []
        for abs_file_path in found_files:
            rel_path = coder.get_rel_fname(abs_file_path)
            # Double check it's not already added somehow
            if abs_file_path not in coder.abs_fnames and abs_file_path not in coder.abs_read_only_fnames:
                # Use explicit=True for clear output, even though it's an external search result
                add_result = coder._add_file_to_context(rel_path, explicit=True)
                if "Added" in add_result or "Viewed" in add_result: # Count successful adds/views
                    added_count += 1
                    added_files_rel.append(rel_path)

        if added_count > 0:
            if added_count > 5:
                brief = ', '.join(added_files_rel[:5]) + f', and {added_count-5} more'
                coder.io.tool_output(f"🔎 Found '{symbol}' and added {added_count} files: {brief}")
            else:
                coder.io.tool_output(f"🔎 Found '{symbol}' and added files: {', '.join(added_files_rel)}")
            return f"Found symbol '{symbol}' and added {added_count} files as read-only."
        else:
            coder.io.tool_output(f"⚠️ Symbol '{symbol}' not found in searchable files (outside current context).")
            return f"Symbol '{symbol}' not found in searchable files (outside current context)."

    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesWithSymbol: {str(e)}")
        return f"Error: {str(e)}"