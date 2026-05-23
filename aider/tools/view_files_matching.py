import re
import os
import fnmatch

def execute_view_files_matching(coder, search_pattern, file_pattern=None, regex=False):
    """
    Search for pattern (literal string or regex) in files and add matching files to context as read-only.

    Args:
        coder: The Coder instance.
        search_pattern (str): The pattern to search for. Treated as a literal string by default.
        file_pattern (str, optional): Glob pattern to filter which files are searched. Defaults to None (search all files).
        regex (bool, optional): If True, treat search_pattern as a regular expression. Defaults to False.

    This tool lets the LLM search for content within files, mimicking
    how a developer would use grep or regex search to find relevant code.
    """
    try:
        # Get list of files to search
        if file_pattern:
            # Use glob pattern to filter files
            all_files = coder.get_all_relative_files()
            files_to_search = []
            for file in all_files:
                if fnmatch.fnmatch(file, file_pattern):
                    files_to_search.append(file)
                    
            if not files_to_search:
                return f"No files matching '{file_pattern}' to search for pattern '{search_pattern}'"
        else:
            # Search all files if no pattern provided
            files_to_search = coder.get_all_relative_files()
        
        # Search for pattern in files
        matches = {}
        for file in files_to_search:
            abs_path = coder.abs_root_path(file)
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match_count = 0
                    if regex:
                        try:
                            matches_found = re.findall(search_pattern, content)
                            match_count = len(matches_found)
                        except re.error as e:
                            # Handle invalid regex patterns gracefully
                            coder.io.tool_error(f"Invalid regex pattern '{search_pattern}': {e}")
                            # Skip this file for this search if regex is invalid
                            continue 
                    else:
                        # Exact string matching
                        match_count = content.count(search_pattern)
                        
                    if match_count > 0:
                        matches[file] = match_count
            except Exception:
                # Skip files that can't be read (binary, etc.)
                pass
                
        # Limit the number of files added if there are too many matches
        if len(matches) > coder.max_files_per_glob:
            coder.io.tool_output(
                f"⚠️ Found '{search_pattern}' in {len(matches)} files, "
                f"limiting to {coder.max_files_per_glob} files with most matches."
            )
            # Sort by number of matches (most matches first)
            sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
            matches = dict(sorted_matches[:coder.max_files_per_glob])
            
        # Add matching files to context
        for file in matches:
            coder._add_file_to_context(file)
        
        # Return a user-friendly result
        if matches:
            # Sort by number of matches (most matches first)
            sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
            match_list = [f"{file} ({count} matches)" for file, count in sorted_matches[:5]]
            
            if len(sorted_matches) > 5:
                coder.io.tool_output(f"🔍 Found '{search_pattern}' in {len(matches)} files: {', '.join(match_list)} and {len(matches)-5} more")
                return f"Found in {len(matches)} files: {', '.join(match_list)} and {len(matches)-5} more"
            else:
                coder.io.tool_output(f"🔍 Found '{search_pattern}' in: {', '.join(match_list)}")
                return f"Found in {len(matches)} files: {', '.join(match_list)}"
        else:
            coder.io.tool_output(f"⚠️ Pattern '{search_pattern}' not found in any files")
            return f"Pattern not found in any files"
    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesMatching: {str(e)}")
        return f"Error: {str(e)}"