from collections import namedtuple
from pygments import lexers, token, util
import os
import argparse # Added
import sys # Added

Tag = namedtuple("Tag", "rel_fname fname line name kind".split())

def get_tags_raw_simplified(fname: str, rel_fname: str):
    try:
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except OSError:
        return []

    if not code:
        return []

    try:
        lexer = lexers.guess_lexer_for_filename(fname, code)
    except util.ClassNotFound:
        return []
    except Exception:
        return []

    # Line numbers are determined by counting newlines from the start of the code
    # to the token's starting index for accuracy, rather than incrementally.
    relevant_token_types = (
        token.Name,
        token.Name.Function,
        token.Name.Class,
        token.Name.Namespace,
        token.Name.Variable,
    )

    try:
        tokens = lexer.get_tokens_unprocessed(code)
    except Exception:
        return []

    for index, ttype, value in tokens:
        if ttype in relevant_token_types:
            token_start_line = code.count('\n', 0, index) + 1

            yield Tag(
                rel_fname=rel_fname,
                fname=fname,
                line=token_start_line,
                name=value.strip(),
                kind=str(ttype)
            )

def get_tags_simplified(fname: str, rel_fname: str):
    yield from get_tags_raw_simplified(fname, rel_fname)

def get_ranked_tags_simplified(root_dir: str, other_fnames: list[str]):
    collected_tags = []
    for fname_abs_path_in in other_fnames: # Renamed to avoid confusion with outer scope
        try:
            fname_abs_path = fname_abs_path_in # Use a new var for modification
            if not os.path.isabs(fname_abs_path) and root_dir:
                 fname_abs_path = os.path.abspath(os.path.join(root_dir, fname_abs_path))
            elif not os.path.isabs(fname_abs_path):
                 fname_abs_path = os.path.abspath(fname_abs_path)

            if root_dir:
                rel_fname = os.path.relpath(fname_abs_path, root_dir)
            else:
                rel_fname = os.path.basename(fname_abs_path)

        except ValueError:
            rel_fname = os.path.basename(fname_abs_path)

        tags_for_file = get_tags_simplified(fname=fname_abs_path, rel_fname=rel_fname)
        collected_tags.extend(tags_for_file)

    collected_tags.sort(key=lambda tag: (tag.rel_fname, tag.line))
    return collected_tags

def render_tree_simplified(abs_fname: str, lois: list[int], context_lines: int = 2, max_line_len: int = 120):
    if not lois:
        return ""

    try:
        with open(abs_fname, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except OSError:
        return f"    [Error reading file: {os.path.basename(abs_fname)}]\n"

    if not lines:
        return ""

    output_lines = []
    # Ensure LOIs are 1-indexed for processing, then convert to 0-indexed for list access
    # Also ensure they are within valid line range for the file.
    valid_lois_1_indexed = sorted(list(set(loi for loi in lois if 0 < loi <= len(lines))))

    if not valid_lois_1_indexed: # if no valid LOIs after filtering
        return ""

    sorted_lois_0_indexed = [loi - 1 for loi in valid_lois_1_indexed]


    regions = []
    for loi_idx in sorted_lois_0_indexed: # These are already 0-indexed
        start_line = max(0, loi_idx - context_lines)
        end_line = min(len(lines) - 1, loi_idx + context_lines)

        if not regions or regions[-1][1] < start_line - 1 :
            regions.append([start_line, end_line])
        else:
            regions[-1][1] = max(regions[-1][1], end_line)

    for i, (start, end) in enumerate(regions):
        if i > 0:
            output_lines.append("    ...")
        for line_num_0_indexed in range(start, end + 1):
            prefix = "  * " if line_num_0_indexed in sorted_lois_0_indexed else "    "
            line_content = lines[line_num_0_indexed].rstrip('\n')

            if len(line_content) > max_line_len:
                line_content = line_content[:max_line_len-3] + "..."
            output_lines.append(f"{prefix}{line_num_0_indexed+1:4d}: {line_content}")

    return "\n".join(output_lines) + "\n" if output_lines else ""


def to_tree_simplified(ranked_tags: list, chat_rel_fnames: set[str], root_dir: str):
    output = []
    current_rel_fname = None
    lois_for_current_file = []
    abs_fname_for_current_file = None

    dummy_marker = object()
    if ranked_tags:
        dummy_tag_rel_fname = f"__dummy_file_marker__{id(dummy_marker)}"
        dummy_tag = Tag(rel_fname=dummy_tag_rel_fname, fname="", line=0, name="", kind="")
        tags_to_process = ranked_tags + [dummy_tag]
    else:
        tags_to_process = []

    for tag in tags_to_process:
        is_dummy_tag = hasattr(tag, 'rel_fname') and tag.rel_fname.startswith("__dummy_file_marker__")

        if tag.rel_fname != current_rel_fname:
            if current_rel_fname is not None and current_rel_fname not in chat_rel_fnames:
                output.append(f"{current_rel_fname}:\n")
                if lois_for_current_file and abs_fname_for_current_file:
                    unique_sorted_lois = sorted(list(set(lois_for_current_file)))
                    rendered_file_tree = render_tree_simplified(
                        abs_fname_for_current_file,
                        unique_sorted_lois
                    )
                    if rendered_file_tree.strip():
                        output.append(rendered_file_tree)
                output.append("\n")

            if not is_dummy_tag:
                current_rel_fname = tag.rel_fname
                if os.path.isabs(tag.fname):
                    abs_fname_for_current_file = tag.fname
                elif root_dir :
                    # Use rel_fname from tag, not current_rel_fname, as current_rel_fname might be from previous iteration
                    abs_fname_for_current_file = os.path.abspath(os.path.join(root_dir, tag.rel_fname))
                else:
                    abs_fname_for_current_file = os.path.abspath(tag.fname)
                lois_for_current_file = []

        if not is_dummy_tag and current_rel_fname not in chat_rel_fnames : # Check current_rel_fname for exclusion
            if tag.line > 0:
                 lois_for_current_file.append(tag.line)

    return "".join(output).rstrip()


def get_repo_map_simplified(root_dir: str, chat_files: list[str], other_files: list[str], max_output_chars: int = 0):
    if not os.path.isabs(root_dir):
        root_dir = os.path.abspath(root_dir)

    chat_rel_fnames = set(chat_files)
    ranked_tags = get_ranked_tags_simplified(root_dir=root_dir, other_fnames=other_files)
    repo_map_str = to_tree_simplified(ranked_tags=ranked_tags, chat_rel_fnames=chat_rel_fnames, root_dir=root_dir)

    if max_output_chars > 0 and len(repo_map_str) > max_output_chars:
        cutoff_point = repo_map_str.rfind('\n', 0, max_output_chars)
        if cutoff_point == -1 or cutoff_point > max_output_chars : # if no newline or newline is after max_chars
             cutoff_point = max_output_chars # simple truncate

        # Ensure we don't cut off so much that "...truncated]" itself is too long
        # This is a basic safety, more complex logic might be needed for very small max_output_chars
        ellipsis = "\n[...truncated]"
        if cutoff_point + len(ellipsis) > max_output_chars and max_output_chars > len(ellipsis):
            cutoff_point = max_output_chars - len(ellipsis)

        repo_map_str = repo_map_str[:cutoff_point] + ellipsis

    return repo_map_str

def main():
    parser = argparse.ArgumentParser(description="Generates a simplified repository map.")
    parser.add_argument(
        "--root",
        required=True,
        help="The absolute path to the repository's root directory."
    )
    parser.add_argument(
        "--chat-files",
        nargs='*',
        default=[],
        help="A list of file paths (relative to --root) already in chat context, to be excluded from the map."
    )
    parser.add_argument(
        "--other-files",
        nargs='+',
        required=True,
        help="A list of file paths (absolute, or relative to current working directory) "
             "to consider for mapping. These will be resolved to absolute paths."
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Optional. If positive, the output string will be truncated to this many characters."
    )

    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    if not os.path.isdir(root_dir):
        print(f"Error: Root directory '{root_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)

    other_files_abs = []
    for f_path in args.other_files:
        # Resolve path: if not absolute, assume relative to CWD initially
        potential_abs_path = os.path.abspath(f_path)

        if os.path.isfile(potential_abs_path):
            other_files_abs.append(potential_abs_path)
        else:
            # Try resolving relative to root_dir if not found at CWD-relative/absolute
            potential_abs_path_from_root = os.path.abspath(os.path.join(root_dir, f_path))
            if os.path.isfile(potential_abs_path_from_root):
                other_files_abs.append(potential_abs_path_from_root)
            else:
                print(f"Warning: File '{f_path}' (tried as '{potential_abs_path}' and '{potential_abs_path_from_root}') not found or is not a file. Skipping.", file=sys.stderr)

    if not other_files_abs:
        # Check if args.other_files was empty to begin with, or if all resolved paths were invalid.
        if not args.other_files: # This case is blocked by nargs='+'
             print("Error: --other-files argument is required.", file=sys.stderr)
        else:
             print("Error: No valid files found in --other-files after validation.", file=sys.stderr)
        sys.exit(1)

    repo_map_str = get_repo_map_simplified(
        root_dir=root_dir,
        chat_files=args.chat_files,
        other_files=other_files_abs, # Pass the validated, absolute paths
        max_output_chars=args.max_chars
    )

    print(repo_map_str)

if __name__ == '__main__':
    main()
