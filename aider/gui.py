#!/usr/bin/env python

import fnmatch
import os
import random
import sys

import streamlit as st

from aider import urls
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.main import main as cli_main
from aider.scrape import Scraper, has_playwright


class CaptureIO(InputOutput):
    lines = []

    def tool_output(self, msg, log_only=False):
        if not log_only:
            self.lines.append(msg)
        super().tool_output(msg, log_only=log_only)

    def tool_error(self, msg):
        self.lines.append(msg)
        super().tool_error(msg)

    def tool_warning(self, msg):
        self.lines.append(msg)
        super().tool_warning(msg)

    def get_captured_lines(self):
        lines = self.lines
        self.lines = []
        return lines


def search(text=None):
    results = []
    for root, _, files in os.walk("aider"):
        for file in files:
            path = os.path.join(root, file)
            if not text or text in path:
                results.append(path)
    # dump(results)

    return results


def format_path_for_display(path, max_len=00, separators=("/","\\")):
    """
    Formats a path for display, prioritizing filename and parent directory.
    Tries to show:
    1. Full path if it fits.
    2. .../parent/filename if it fits.
    3. .../filename if it fits.
    4. Simple left truncation as a fallback.
    """
    if len(path) <= max_len:
        return path

    sep = os.sep  # Use the OS-specific separator

    try:
        filename = os.path.basename(path)
        dirname = os.path.dirname(path)
        parent_dir = os.path.basename(dirname)

        # Try .../parent/filename
        if parent_dir:
             short_path = os.path.join("...", parent_dir, filename)
        else:
             short_path = os.path.join("...", filename)


        if len(short_path) <= max_len:
             simple_truncated = "..." + path[-(max_len - 3):]
             if len(short_path) <= len(simple_truncated):
                 return short_path
             else:
                 return simple_truncated

        # Try .../filename if .../parent/filename was too long or parent didn't exist
        short_path_fname_only = os.path.join("...", filename)
        if len(short_path_fname_only) <= max_len:
             return short_path_fname_only

        # Fallback: Simple left truncation if nothing else fits
        return "..." + path[-(max_len - 3):]

    except Exception:
        # Safety fallback in case of weird paths
        return "..." + path[-(max_len - 3):]


# Keep state as a resource, which survives browser reloads (since Coder does too)
class State:
    keys = set()

    def init(self, key, val=None):
        if key in self.keys:
            return

        self.keys.add(key)
        setattr(self, key, val)
        return True


@st.cache_resource
def get_state():
    return State()


@st.cache_resource
def get_coder():
    coder = cli_main(return_coder=True)
    if not isinstance(coder, Coder):
        raise ValueError(coder)
    if not coder.repo:
        raise ValueError("GUI can currently only be used inside a git repo")

    io = CaptureIO(
        pretty=False,
        yes=True,
        dry_run=coder.io.dry_run,
        encoding=coder.io.encoding,
    )
    # coder.io = io # this breaks the input_history
    coder.commands.io = io

    for line in coder.get_announcements():
        coder.io.tool_output(line)

    return coder


class GUI:
    prompt = None
    prompt_as = "user"
    last_undo_empty = None
    recent_msgs_empty = None
    web_content_empty = None
    folder_content_empty = None

    def filter_files(self, files, allow_patterns_str, deny_patterns_str):
        allow_patterns = [p.strip() for p in allow_patterns_str.splitlines() if p.strip()]
        deny_patterns = [p.strip() for p in deny_patterns_str.splitlines() if p.strip()]

        filtered_files = files

        if allow_patterns:
            allowed_set = set()
            for pattern in allow_patterns:
                allowed_set.update(fnmatch.filter(files, pattern))
            filtered_files = list(allowed_set)

        if deny_patterns:
            denied_set = set()
            for pattern in deny_patterns:
                denied_set.update(fnmatch.filter(filtered_files, pattern))
            filtered_files = [f for f in filtered_files if f not in denied_set]

        return sorted(filtered_files)

    def announce(self):
        lines = self.coder.get_announcements()
        lines = "  \n".join(lines)
        return lines

    def show_edit_info(self, edit):
        commit_hash = edit.get("commit_hash")
        commit_message = edit.get("commit_message")
        diff = edit.get("diff")
        fnames = edit.get("fnames")
        if fnames:
            fnames = sorted(fnames)

        if not commit_hash and not fnames:
            return

        show_undo = False
        res = ""
        if commit_hash:
            res += f"Commit `{commit_hash}`: {commit_message}  \n"
            if commit_hash == self.coder.last_aider_commit_hash:
                show_undo = True

        if fnames:
            fnames = [f"`{fname}`" for fname in fnames]
            fnames = ", ".join(fnames)
            res += f"Applied edits to {fnames}."

        if diff:
            with st.expander(res):
                st.code(diff, language="diff")
                if show_undo:
                    self.add_undo(commit_hash)
        else:
            with st.container(border=True):
                st.write(res)
                if show_undo:
                    self.add_undo(commit_hash)

    def add_undo(self, commit_hash):
        if self.last_undo_empty:
            self.last_undo_empty.empty()

        self.last_undo_empty = st.empty()
        undone = self.state.last_undone_commit_hash == commit_hash
        if not undone:
            with self.last_undo_empty:
                if self.button(f"Undo commit `{commit_hash}`", key=f"undo_{commit_hash}"):
                    self.do_undo(commit_hash)

    def do_sidebar(self):
        with st.sidebar:
            st.title("Aider")
            # self.cmds_tab, self.settings_tab = st.tabs(["Commands", "Settings"])

            # self.do_recommended_actions()
            self.do_add_to_chat()
            self.do_recent_msgs()
            self.do_clear_chat_history()
            # st.container(height=150, border=False)
            # st.write("### Experimental")

            st.warning(
                "This browser version of aider is experimental. Please share feedback in [GitHub"
                " issues](https://github.com/Aider-AI/aider/issues)."
            )

    def do_settings_tab(self):
        pass

    def do_recommended_actions(self):
        text = "Aider works best when your code is stored in a git repo.  \n"
        text += f"[See the FAQ for more info]({urls.git})"

        with st.expander("Recommended actions", expanded=True):
            with st.popover("Create a git repo to track changes"):
                st.write(text)
                self.button("Create git repo", key=random.random(), help="?")

            with st.popover("Update your `.gitignore` file"):
                st.write("It's best to keep aider's internal files out of your git repo.")
                self.button("Add `.aider*` to `.gitignore`", key=random.random(), help="?")

    def do_add_to_chat(self):
        # with st.expander("Add to the chat", expanded=True):
        self.do_add_files_multiselect()
        self.do_add_folder()
        self.do_add_files_filter_ui()
        st.divider()
        self.do_add_web_page()

    def do_add_files_multiselect(self):
        # Initialize state if needed (might be set by filter UI first)
        if 'allow_patterns' not in st.session_state:
            st.session_state.allow_patterns = ""
        if 'deny_patterns' not in st.session_state:
            st.session_state.deny_patterns = ""

        # --- Apply Filtering (reads state set by filter UI) ---
        all_files = self.coder.get_all_relative_files()
        filtered_options = self.filter_files(
            all_files,
            st.session_state.allow_patterns,
            st.session_state.deny_patterns
        )

        current_inchat_files = self.coder.get_inchat_relative_files()
        current_inchat_files_set = set(current_inchat_files)
        widget_key = "multiselect_add_files"

        options_for_widget = sorted(list(set(filtered_options) | current_inchat_files_set))

        # --- Render Multiselect ---
        fnames_selected_in_widget = st.multiselect(
            "Add files to the chat",
            options=options_for_widget,
            default=current_inchat_files,
            key=widget_key,
            placeholder="Type to search or select files...",
            disabled=self.prompt_pending(),
            format_func=lambda path: format_path_for_display(path, max_len=60),
            help=(
                "Select files to edit. Use filter controls below to narrow down this list. "
                "Aider automatically includes relevant context from other files."
            ),
        )
        fnames_selected_in_widget_set = set(fnames_selected_in_widget)

        # --- Handle adding/removing files ---
        files_to_add = fnames_selected_in_widget_set - current_inchat_files_set
        files_to_remove = current_inchat_files_set - fnames_selected_in_widget_set

        for fname in files_to_add:
            full_path = os.path.join(self.coder.root, fname)
            if os.path.exists(full_path):
                self.coder.add_rel_fname(fname)
                self.info(f"Added `{fname}` to the chat")
            else:
                 st.warning(f"Could not add `{fname}` as it seems to no longer exist.")

        for fname in files_to_remove:
            self.coder.drop_rel_fname(fname)
            self.info(f"Removed `{fname}` from the chat")

    # --- New method to render just the filter UI ---
    def do_add_files_filter_ui(self):
        # Initialize state if needed (might be set by multiselect first)
        if 'allow_patterns' not in st.session_state:
            st.session_state.allow_patterns = ""
        if 'deny_patterns' not in st.session_state:
            st.session_state.deny_patterns = ""

        # --- Render Filter Expander ---
        with st.expander("Add file filters"):
            allow_patterns_input = st.text_area(
                "Allow patterns (globs)",
                value=st.session_state.allow_patterns,
                key="allow_patterns_input",
                help="Show only files matching these glob patterns (e.g., `*.py`, `src/**`), one per line. Applied first.",
                height=68,
                disabled=self.prompt_pending(),
                placeholder="*.py\nsrc/**"
            )
            deny_patterns_input = st.text_area(
                "Deny patterns (globs)",
                value=st.session_state.deny_patterns,
                key="deny_patterns_input",
                help="Hide files matching these glob patterns (e.g., `.venv/*`, `*.log`), one per line. Applied after allow patterns.",
                height=68,
                disabled=self.prompt_pending(),
                placeholder=".venv/*\n*.log"
            )
            # Update session state when inputs change (triggers rerun)
            st.session_state.allow_patterns = allow_patterns_input
            st.session_state.deny_patterns = deny_patterns_input


    def do_add_folder(self):
        # --- This function remains unchanged ---
        with st.popover("Add a folder to the chat"):
            st.markdown("Add all *tracked* files from a folder to the chat (ignores filters)")

            folder_input_key = f"folder_content_{self.state.folder_content_num}"
            self.folder_content = st.text_input(
                "Folder path",
                placeholder="path/to/folder",
                key=folder_input_key,
                disabled=self.prompt_pending(),
            )

            if self.folder_content:
                clean_folder_path = os.path.normpath(self.folder_content)
                if not clean_folder_path or clean_folder_path == '.':
                    st.warning("Please enter a valid folder path.")
                    return

                if not self.coder or not self.coder.repo:
                    st.error("Error: Coder or Git repository not initialized correctly.")
                    return

                try:
                    tracked_files_set = self.coder.repo.get_tracked_files()
                except Exception as e:
                    st.error(f"Error getting tracked files from git: {e}")
                    return

                all_files = self.coder.get_all_relative_files()
                inchat_files = set(self.coder.get_inchat_relative_files())

                prefix = clean_folder_path + os.sep
                files_to_consider = [
                    f for f in all_files
                    if f not in inchat_files and (f.startswith(prefix) or f == clean_folder_path)
                ]

                if files_to_consider:
                    button_key = f"add_folder_button_{self.state.folder_content_num}"
                    if st.button("Add all tracked files from folder", key=button_key, disabled=self.prompt_pending()):
                        added_count = 0
                        files_actually_added = []
                        for file_path in files_to_consider:
                            if file_path in tracked_files_set:
                                self.coder.add_rel_fname(file_path)
                                files_actually_added.append(file_path)
                                added_count += 1

                        if added_count > 0:
                            added_files_str = ", ".join(f"`{f}`" for f in files_actually_added)
                            self.info(f"Added {added_count} tracked files from `{clean_folder_path}` to the chat: {added_files_str}")
                            self.state.folder_content_num += 1
                            self.folder_content = ""
                            st.rerun()
                        else:
                            st.warning(f"No *new*, *tracked* files found in folder `{clean_folder_path}` to add.")

                elif self.folder_content:
                     is_single_tracked_file_not_in_chat = clean_folder_path in tracked_files_set and clean_folder_path not in inchat_files
                     if is_single_tracked_file_not_in_chat:
                          button_key = f"add_folder_button_{self.state.folder_content_num}"
                          if st.button(f"Add file `{clean_folder_path}`", key=button_key, disabled=self.prompt_pending()):
                               self.coder.add_rel_fname(clean_folder_path)
                               self.info(f"Added `{clean_folder_path}` to the chat")
                               self.state.folder_content_num += 1
                               self.folder_content = ""
                               st.rerun()
                     elif not os.path.isdir(os.path.join(self.coder.root, clean_folder_path)) and not is_single_tracked_file_not_in_chat:
                         st.warning(f"Path `{clean_folder_path}` is not a valid folder or tracked file in the repository.")
                     else:
                         st.warning(f"No *new*, *tracked* files found in folder `{clean_folder_path}`.")

    def do_add_web_page(self):
        with st.popover("Add a web page to the chat"):
            self.do_web()

    def do_add_image(self):
        with st.popover("Add image"):
            st.markdown("Hello World 👋")
            st.file_uploader("Image file", disabled=self.prompt_pending())

    def do_run_shell(self):
        with st.popover("Run shell commands, tests, etc"):
            st.markdown(
                "Run a shell command and optionally share the output with the LLM. This is"
                " a great way to run your program or run tests and have the LLM fix bugs."
            )
            st.text_input("Command:")
            st.radio(
                "Share the command output with the LLM?",
                [
                    "Review the output and decide whether to share",
                    "Automatically share the output on non-zero exit code (ie, if any tests fail)",
                ],
            )
            st.selectbox(
                "Recent commands",
                [
                    "my_app.py --doit",
                    "my_app.py --cleanup",
                ],
                disabled=self.prompt_pending(),
            )

    def do_tokens_and_cost(self):
        with st.expander("Tokens and costs", expanded=True):
            pass

    def do_show_token_usage(self):
        with st.popover("Show token usage"):
            st.write("hi")

    def do_clear_chat_history(self):
        text = "Saves tokens, reduces confusion"
        if self.button("Clear chat history", help=text):
            self.coder.done_messages = []
            self.coder.cur_messages = []
            self.info("Cleared chat history. Now the LLM can't see anything before this line.")

    def do_show_metrics(self):
        st.metric("Cost of last message send & reply", "$0.0019", help="foo")
        st.metric("Cost to send next message", "$0.0013", help="foo")
        st.metric("Total cost this session", "$0.22")

    def do_git(self):
        with st.expander("Git", expanded=False):
            # st.button("Show last diff")
            # st.button("Undo last commit")
            self.button("Commit any pending changes")
            with st.popover("Run git command"):
                st.markdown("## Run git command")
                st.text_input("git", value="git ")
                self.button("Run")
                st.selectbox(
                    "Recent git commands",
                    [
                        "git checkout -b experiment",
                        "git stash",
                    ],
                    disabled=self.prompt_pending(),
                )

    def do_recent_msgs(self):
        if not self.recent_msgs_empty:
            self.recent_msgs_empty = st.empty()

        if self.prompt_pending():
            self.recent_msgs_empty.empty()
            self.state.recent_msgs_num += 1

        with self.recent_msgs_empty:
            self.old_prompt = st.selectbox(
                "Resend a recent chat message",
                self.state.input_history,
                placeholder="Choose a recent chat message",
                # label_visibility="collapsed",
                index=None,
                key=f"recent_msgs_{self.state.recent_msgs_num}",
                disabled=self.prompt_pending(),
            )
            if self.old_prompt:
                self.prompt = self.old_prompt

    def do_messages_container(self):
        self.messages = st.container()

        # stuff a bunch of vertical whitespace at the top
        # to get all the chat text to the bottom
        # self.messages.container(height=300, border=False)

        with self.messages:
            for msg in self.state.messages:
                role = msg["role"]

                if role == "edit":
                    self.show_edit_info(msg)
                elif role == "info":
                    st.info(msg["content"])
                elif role == "text":
                    text = msg["content"]
                    line = text.splitlines()[0]
                    with self.messages.expander(line):
                        st.text(text)
                elif role in ("user", "assistant"):
                    with st.chat_message(role):
                        st.write(msg["content"])
                        # self.cost()
                else:
                    st.dict(msg)

    def initialize_state(self):
        messages = [
            dict(role="info", content=self.announce()),
            dict(role="assistant", content="How can I help you?"),
        ]

        self.state.init("messages", messages)
        self.state.init("last_aider_commit_hash", self.coder.last_aider_commit_hash)
        self.state.init("last_undone_commit_hash")
        self.state.init("recent_msgs_num", 0)
        self.state.init("web_content_num", 0)
        self.state.init("folder_content_num", 0)
        self.state.init("prompt")
        self.state.init("scraper")

        self.state.init("initial_inchat_files", self.coder.get_inchat_relative_files())

        if "input_history" not in self.state.keys:
            input_history = list(self.coder.io.get_input_history())
            seen = set()
            input_history = [x for x in input_history if not (x in seen or seen.add(x))]
            self.state.input_history = input_history
            self.state.keys.add("input_history")

    def button(self, args, **kwargs):
        "Create a button, disabled if prompt pending"

        # Force everything to be disabled if there is a prompt pending
        if self.prompt_pending():
            kwargs["disabled"] = True

        return st.button(args, **kwargs)

    def __init__(self):
        self.coder = get_coder()
        self.state = get_state()

        # Force the coder to cooperate, regardless of cmd line args
        self.coder.yield_stream = True
        self.coder.stream = True
        self.coder.pretty = False

        self.initialize_state()

        self.do_messages_container()
        self.do_sidebar()

        user_inp = st.chat_input("Say something")
        if user_inp:
            self.prompt = user_inp

        if self.prompt_pending():
            self.process_chat()

        if not self.prompt:
            return

        self.state.prompt = self.prompt

        if self.prompt_as == "user":
            self.coder.io.add_to_input_history(self.prompt)

        self.state.input_history.append(self.prompt)

        if self.prompt_as:
            self.state.messages.append({"role": self.prompt_as, "content": self.prompt})
        if self.prompt_as == "user":
            with self.messages.chat_message("user"):
                st.write(self.prompt)
        elif self.prompt_as == "text":
            line = self.prompt.splitlines()[0]
            line += "??"
            with self.messages.expander(line):
                st.text(self.prompt)

        # re-render the UI for the prompt_pending state
        st.rerun()

    def prompt_pending(self):
        return self.state.prompt is not None

    def cost(self):
        cost = random.random() * 0.003 + 0.001
        st.caption(f"${cost:0.4f}")

    def process_chat(self):
        prompt = self.state.prompt
        self.state.prompt = None

        # This duplicates logic from within Coder
        self.num_reflections = 0
        self.max_reflections = 3

        while prompt:
            with self.messages.chat_message("assistant"):
                res = st.write_stream(self.coder.run_stream(prompt))
                self.state.messages.append({"role": "assistant", "content": res})
                # self.cost()

            prompt = None
            if self.coder.reflected_message:
                if self.num_reflections < self.max_reflections:
                    self.num_reflections += 1
                    self.info(self.coder.reflected_message)
                    prompt = self.coder.reflected_message

        with self.messages:
            edit = dict(
                role="edit",
                fnames=self.coder.aider_edited_files,
            )
            if self.state.last_aider_commit_hash != self.coder.last_aider_commit_hash:
                edit["commit_hash"] = self.coder.last_aider_commit_hash
                edit["commit_message"] = self.coder.last_aider_commit_message
                commits = f"{self.coder.last_aider_commit_hash}~1"
                diff = self.coder.repo.diff_commits(
                    self.coder.pretty,
                    commits,
                    self.coder.last_aider_commit_hash,
                )
                edit["diff"] = diff
                self.state.last_aider_commit_hash = self.coder.last_aider_commit_hash

            self.state.messages.append(edit)
            self.show_edit_info(edit)

        # re-render the UI for the non-prompt_pending state
        st.rerun()

    def info(self, message, echo=True):
        info = dict(role="info", content=message)
        self.state.messages.append(info)

        # We will render the tail of the messages array after this call
        if echo:
            self.messages.info(message)

    def do_web(self):
        st.markdown("Add the text content of a web page to the chat")

        if not self.web_content_empty:
            self.web_content_empty = st.empty()

        if self.prompt_pending():
            self.web_content_empty.empty()
            self.state.web_content_num += 1

        with self.web_content_empty:
            self.web_content = st.text_input(
                "URL",
                placeholder="https://...",
                key=f"web_content_{self.state.web_content_num}",
            )

        if not self.web_content:
            return

        url = self.web_content

        if not self.state.scraper:
            self.scraper = Scraper(print_error=self.info, playwright_available=has_playwright())

        content = self.scraper.scrape(url) or ""
        if content.strip():
            content = f"{url}\n\n" + content
            self.prompt = content
            self.prompt_as = "text"
        else:
            self.info(f"No web content found for `{url}`.")
            self.web_content = None

    def do_undo(self, commit_hash):
        self.last_undo_empty.empty()

        if (
            self.state.last_aider_commit_hash != commit_hash
            or self.coder.last_aider_commit_hash != commit_hash
        ):
            self.info(f"Commit `{commit_hash}` is not the latest commit.")
            return

        self.coder.commands.io.get_captured_lines()
        reply = self.coder.commands.cmd_undo(None)
        lines = self.coder.commands.io.get_captured_lines()

        lines = "\n".join(lines)
        lines = lines.splitlines()
        lines = "  \n".join(lines)
        self.info(lines, echo=False)

        self.state.last_undone_commit_hash = commit_hash

        if reply:
            self.prompt_as = None
            self.prompt = reply


def gui_main():
    st.set_page_config(
        layout="wide",
        page_title="Aider",
        page_icon=urls.favicon,
        menu_items={
            "Get Help": urls.website,
            "Report a bug": "https://github.com/Aider-AI/aider/issues",
            "About": "# Aider\nAI pair programming in your browser.",
        },
    )

    # --- Inject CSS for wider multiselect tags ---
    # NOTE: These selectors target internal Streamlit/BaseWeb structures and might
    # break in future Streamlit versions. Inspect element if styles don't apply.
    st.markdown("""
           <style>
               .stMultiSelect [data-baseweb="tag"] {
                   max-width: 500px;
               }
               /* Optional: Ensure text inside tag respects the width, though format_func handles ellipsis now */
               .stMultiSelect [data-baseweb="tag"] span {
                    display: inline-block;
                    max-width: 100%;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
               }

               /* --- CSS for Dropdown Items (Optional Tweaks) --- */
               /* Target list items within the multiselect popover */
               /* NOTE: Selector might change in future Streamlit versions */
               div[data-baseweb="popover"] ul li {
                   /* Example: Slightly smaller font for dropdown to fit more */
                   /* font-size: 0.95rem; */

                   /* Example: Adjust padding if needed */
                   /* padding-top: 0.2rem; */
                   /* padding-bottom: 0.2rem; */
               }

           </style>
           """, unsafe_allow_html=True)

    # config_options = st.config._config_options
    # for key, value in config_options.items():
    #    print(f"{key}: {value.value}")

    GUI()


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
