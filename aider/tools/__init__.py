# flake8: noqa: F401
# Import tool functions into the aider.tools namespace

from .command import _execute_command, command_schema
from .command_interactive import (
    _execute_command_interactive,
    command_interactive_schema,
)
from .delete_block import _execute_delete_block, delete_block_schema
from .delete_line import _execute_delete_line, delete_line_schema
from .delete_lines import _execute_delete_lines, delete_lines_schema
from .extract_lines import _execute_extract_lines, extract_lines_schema
from .git import (
    _execute_git_diff,
    _execute_git_log,
    _execute_git_show,
    _execute_git_status,
    git_diff_schema,
    git_log_schema,
    git_show_schema,
    git_status_schema,
)
from .grep import _execute_grep, grep_schema
from .indent_lines import _execute_indent_lines, indent_lines_schema
from .insert_block import _execute_insert_block, insert_block_schema
from .list_changes import _execute_list_changes, list_changes_schema
from .ls import execute_ls, ls_schema
from .make_editable import _execute_make_editable, make_editable_schema
from .make_readonly import _execute_make_readonly, make_readonly_schema
from .remove import _execute_remove, remove_schema
from .replace_all import _execute_replace_all, replace_all_schema
from .replace_line import _execute_replace_line, replace_line_schema
from .replace_lines import _execute_replace_lines, replace_lines_schema
from .replace_text import _execute_replace_text, replace_text_schema
from .show_numbered_context import (
    execute_show_numbered_context,
    show_numbered_context_schema,
)
from .undo_change import _execute_undo_change, undo_change_schema
from .update_todo_list import _execute_update_todo_list, update_todo_list_schema
from .view import execute_view, view_schema
from .view_files_at_glob import execute_view_files_at_glob, view_files_at_glob_schema
from .view_files_matching import execute_view_files_matching, view_files_matching_schema
from .view_files_with_symbol import (
    _execute_view_files_with_symbol,
    view_files_with_symbol_schema,
)
