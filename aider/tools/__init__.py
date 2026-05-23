# flake8: noqa: F401
# Import tool functions into the aider.tools namespace

# Discovery
from .ls import execute_ls
from .view_files_at_glob import execute_view_files_at_glob
from .view_files_matching import execute_view_files_matching
from .view_files_with_symbol import _execute_view_files_with_symbol

# Context Management
from .view import execute_view
from .remove import _execute_remove
from .make_editable import _execute_make_editable
from .make_readonly import _execute_make_readonly
from .show_numbered_context import execute_show_numbered_context

# Granular Editing
from .replace_text import _execute_replace_text
from .replace_all import _execute_replace_all
from .insert_block import _execute_insert_block
from .delete_block import _execute_delete_block
from .replace_line import _execute_replace_line
from .replace_lines import _execute_replace_lines
from .indent_lines import _execute_indent_lines
from .extract_lines import _execute_extract_lines
from .delete_line import _execute_delete_line
from .delete_lines import _execute_delete_lines

# Change Tracking
from .undo_change import _execute_undo_change
from .list_changes import _execute_list_changes

# Other
from .command import _execute_command
from .command_interactive import _execute_command_interactive
