import os
import fnmatch

def execute_view_files_matching(coder, search_pattern, file_pattern=None):
    """
    Search for pattern in files and add matching files to context as read-only.

    This tool lets the LLM search for content within files, mimicking
    how a developer would use grep to find relevant code.
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
                    if search_pattern in content:
                        matches[file] = content.count(search_pattern)
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
