#!/usr/bin/env python

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
from aider.generative_bg import inject_generative_background
from aider import skill_loader


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
        if commit_hash:
            if commit_hash == self.coder.last_aider_commit_hash:
                show_undo = True

        # Build file tags HTML
        file_tags_html = ""
        if fnames:
            for fname in fnames:
                basename = os.path.basename(fname)
                file_tags_html += (
                    f'<span class="commit-file-tag" title="{fname}">{basename}</span>'
                )

        if commit_hash:
            card_html = f"""
<div class="commit-card">
  <div class="commit-card-header">
    <span class="commit-hash-badge">{commit_hash}</span>
    <span class="commit-message">{commit_message or ""}</span>
  </div>
  {f'<div class="commit-file-tags">{file_tags_html}</div>' if file_tags_html else ""}
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)
            if diff:
                with st.expander("View diff", expanded=False):
                    st.code(diff, language="diff")
                    if show_undo:
                        self.add_undo(commit_hash)
            elif show_undo:
                self.add_undo(commit_hash)
        elif fnames:
            card_html = f"""
<div class="commit-card">
  <div class="commit-card-header">
    <span class="commit-message">Applied edits</span>
  </div>
  <div class="commit-file-tags">{file_tags_html}</div>
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)

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
            # --- Model badge + project name header ---
            try:
                model_name = self.coder.main_model.name
            except Exception:
                model_name = "unknown"

            try:
                repo_root = self.coder.repo.root
                project_name = os.path.basename(repo_root.rstrip("/\\"))
            except Exception:
                project_name = "project"

            st.markdown(
                f"""
<div class="sidebar-header">
  <div class="sidebar-project-name">{project_name}</div>
  <div class="sidebar-model-badge">{model_name}</div>
</div>
""",
                unsafe_allow_html=True,
            )

            self.do_add_to_chat()
            self.do_recent_msgs()
            self.do_clear_chat_history()
            self.do_skills_panel()

            # De-emphasised experimental notice
            st.markdown(
                '<p class="experimental-notice">Browser UI is experimental. '
                '<a href="https://github.com/Aider-AI/aider/issues" target="_blank">'
                "Share feedback</a></p>",
                unsafe_allow_html=True,
            )

    def do_settings_tab(self):
        pass

    def do_skills_panel(self):
        """Sidebar skills queue — select skills to prepend as invocation prompts on next send."""
        st.markdown("---")

        # Multiselect: pick any skills to queue
        selected_labels = st.multiselect(
            "Queue skills",
            options=self.state.skill_labels,
            default=self.state.queued_skills,
            placeholder="Type / to filter skills...",
            disabled=self.prompt_pending(),
            help=(
                "Select one or more skills to invoke on your next message. "
                "The skill instructions will be prepended to whatever you type."
            ),
            key="skills_multiselect",
        )

        # Persist selection back into state
        self.state.queued_skills = selected_labels

        # Show queued indicator if any skills are selected
        if selected_labels:
            names = [f"/{skill_loader.skill_name_from_label(lbl)}" for lbl in selected_labels]
            queued_display = "  ".join(
                [f'<span class="skill-queue-badge">{n}</span>' for n in names]
            )
            st.markdown(
                f'<div class="skill-queue-indicator">Queued: {queued_display}</div>',
                unsafe_allow_html=True,
            )

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
        self.do_add_files()
        self.do_add_web_page()

    def do_add_files(self):
        fnames = st.multiselect(
            "Add files to the chat",
            self.coder.get_all_relative_files(),
            default=self.state.initial_inchat_files,
            placeholder="Files to edit",
            disabled=self.prompt_pending(),
            help=(
                "Only add the files that need to be *edited* for the task you are working"
                " on. Aider will pull in other relevant code to provide context to the LLM."
            ),
        )

        for fname in fnames:
            if fname not in self.coder.get_inchat_relative_files():
                self.coder.add_rel_fname(fname)
                self.info(f"Added {fname} to the chat")

        for fname in self.coder.get_inchat_relative_files():
            if fname not in fnames:
                self.coder.drop_rel_fname(fname)
                self.info(f"Removed {fname} from the chat")

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
                    content = msg["content"]
                    first_line = content.splitlines()[0] if content else "Info"
                    summary = first_line[:80] + ("..." if len(first_line) > 80 else "")
                    with st.expander(f"ℹ  {summary}", expanded=False):
                        st.markdown(content)
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
        self.state.init("prompt")
        self.state.init("scraper")

        self.state.init("initial_inchat_files", self.coder.get_inchat_relative_files())

        # Skills autocomplete state
        self.state.init("skills", skill_loader.load_skills())
        self.state.init("queued_skills", [])
        self.state.init("skill_labels", skill_loader.build_skill_option_labels(self.state.skills))

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

        user_inp = st.chat_input("Ask me to edit code...")
        if user_inp:
            self.prompt = user_inp

            # If skills are queued, prepend their invocation prompts and clear the queue
            if self.state.queued_skills:
                skill_names = [
                    skill_loader.skill_name_from_label(lbl)
                    for lbl in self.state.queued_skills
                ]
                skill_prompt = skill_loader.get_multi_skill_prompt(skill_names)
                # Combine skill invocation with the user's actual message
                if user_inp.strip():
                    self.prompt = skill_prompt + "\n\n" + user_inp
                else:
                    self.prompt = skill_prompt
                self.state.queued_skills = []

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
                with st.spinner("Thinking..."):
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

        # Render inline as collapsible expander
        if echo:
            first_line = message.splitlines()[0] if message else "Info"
            summary = first_line[:80] + ("..." if len(first_line) > 80 else "")
            with self.messages.expander(f"ℹ  {summary}", expanded=False):
                st.markdown(message)

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


def inject_custom_css():
    st.markdown(
        """
<style>
/* ============================================================
   AIDER DARK THEME — claude.ai-inspired premium dark mode
   ============================================================ */

/* --- Root palette --- */
:root {
    --bg-base:        #0d1117;
    --bg-surface:     #161b22;
    --bg-elevated:    #1c2128;
    --bg-hover:       #21262d;
    --bg-sidebar:     #0f1318;
    --border:         rgba(48, 54, 61, 0.8);
    --border-subtle:  rgba(48, 54, 61, 0.4);
    --accent:         #58a6ff;
    --accent-dim:     rgba(88, 166, 255, 0.12);
    --accent-glow:    rgba(88, 166, 255, 0.25);
    --text-primary:   #e6edf3;
    --text-secondary: #8b949e;
    --text-muted:     #484f58;
    --user-bubble-bg: rgba(88, 166, 255, 0.10);
    --user-bubble-border: rgba(88, 166, 255, 0.25);
    --assistant-bubble-border: rgba(48, 54, 61, 0.6);
    --success:        #3fb950;
    --warning:        #d29922;
    --error:          #f85149;
    --radius-sm:      6px;
    --radius-md:      10px;
    --radius-lg:      14px;
    --font-sans:      -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Helvetica, Arial, sans-serif;
    --font-mono:      "JetBrains Mono", "Fira Code", "Cascadia Code", ui-monospace, SFMono-Regular, Menlo, monospace;
    --transition:     0.18s ease;
}

/* --- Global page background --- */
.stApp, .main, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
}

/* --- Keep header functional, only hide deploy button and footer --- */
footer {
    display: none !important;
}
header[data-testid="stHeader"] {
    background-color: var(--bg-surface) !important;
    border-bottom: 1px solid var(--border) !important;
    backdrop-filter: blur(12px) !important;
}
/* Ensure header buttons (sidebar toggle, stop, menu) are visible */
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] [data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    color: var(--text-primary) !important;
    opacity: 1 !important;
    visibility: visible !important;
}
[data-testid="stToolbar"] {
    background-color: transparent !important;
}
.stDeployButton {
    display: none !important;
}

/* --- Main content area padding --- */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* --- Sidebar --- */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] h1 {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: var(--text-primary) !important;
    margin-bottom: 1rem !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* --- Multiselect (file picker) --- */
[data-testid="stMultiSelect"] > div {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
}
[data-testid="stMultiSelect"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background-color: var(--accent-dim) !important;
    border: 1px solid var(--user-bubble-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--accent) !important;
    font-size: 0.8rem !important;
}

/* --- Selectbox / dropdowns --- */
[data-testid="stSelectbox"] > div > div {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}

/* --- Text inputs --- */
[data-testid="stTextInput"] input {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
    outline: none !important;
}

/* --- Chat input (main prompt bar) --- */
[data-testid="stChatInput"] {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.1rem 0.25rem !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
    backdrop-filter: blur(8px) !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim), 0 4px 24px rgba(0,0,0,0.4) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
    font-size: 0.95rem !important;
    caret-color: var(--accent) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-muted) !important;
}
[data-testid="stChatInputSubmitButton"] button {
    background-color: var(--accent) !important;
    border-radius: var(--radius-sm) !important;
    border: none !important;
    transition: opacity var(--transition) !important;
}
[data-testid="stChatInputSubmitButton"] button:hover {
    opacity: 0.85 !important;
}

/* --- Chat messages: container --- */
[data-testid="stChatMessageContent"] {
    font-family: var(--font-sans) !important;
    font-size: 0.93rem !important;
    line-height: 1.7 !important;
    color: var(--text-primary) !important;
}

/* --- Chat messages: user bubble --- */
[data-testid="stChatMessage"][data-testid*="user"],
.stChatMessage[aria-label*="user"] {
    background-color: var(--user-bubble-bg) !important;
    border: 1px solid var(--user-bubble-border) !important;
    border-radius: var(--radius-lg) !important;
    margin: 0.5rem 0 !important;
    padding: 0.75rem 1rem !important;
    backdrop-filter: blur(4px) !important;
}

/* --- Chat messages: assistant bubble --- */
[data-testid="stChatMessage"][data-testid*="assistant"],
.stChatMessage[aria-label*="assistant"] {
    background-color: transparent !important;
    border: 1px solid var(--assistant-bubble-border) !important;
    border-radius: var(--radius-lg) !important;
    margin: 0.5rem 0 !important;
    padding: 0.75rem 1rem !important;
}

/* ALL avatars hidden — design decision, distinguish messages by styling not icons */
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessageAvatarContainer"],
.stChatMessageAvatarContainer {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}

/* --- Code blocks --- */
pre, code {
    font-family: var(--font-mono) !important;
    font-size: 0.875rem !important;
    font-feature-settings: "liga" 1, "calt" 1 !important;
}
pre {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 1rem 1.25rem !important;
    overflow-x: auto !important;
}
code:not(pre code) {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 4px !important;
    padding: 0.15em 0.4em !important;
    color: #d2a8ff !important;
}
/* Streamlit's syntax highlight wrapper */
.stCodeBlock pre {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
}
.stCodeBlock code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: inherit !important;
}

/* --- Expanders (diff views, etc.) --- */
[data-testid="stExpander"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stExpander"]:hover {
    border-color: var(--accent) !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] > div {
    background-color: var(--bg-elevated) !important;
    border-top: 1px solid var(--border) !important;
}

/* --- Containers with border --- */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    backdrop-filter: blur(4px) !important;
}

/* --- Buttons --- */
.stButton > button {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-sans) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.9rem !important;
    transition: background-color var(--transition), border-color var(--transition), box-shadow var(--transition) !important;
}
.stButton > button:hover {
    background-color: var(--bg-hover) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent-dim) !important;
    color: var(--accent) !important;
}
.stButton > button:active {
    background-color: var(--accent-dim) !important;
}
/* Undo button — give it a subtle warning tint */
.stButton > button[kind="secondary"] {
    border-color: rgba(210, 153, 34, 0.4) !important;
    color: var(--warning) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--warning) !important;
    background-color: rgba(210, 153, 34, 0.08) !important;
    color: var(--warning) !important;
}

/* --- Popover --- */
[data-testid="stPopover"] > div {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
    backdrop-filter: blur(12px) !important;
}

/* --- Info / warning / error banners --- */
[data-testid="stInfo"] {
    background-color: var(--accent-dim) !important;
    border: 1px solid var(--accent) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}
[data-testid="stWarning"],
.stAlert[data-baseweb="notification"][kind="warning"] {
    background-color: rgba(210, 153, 34, 0.10) !important;
    border: 1px solid rgba(210, 153, 34, 0.4) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}
[data-testid="stWarning"] a,
[data-testid="stWarning"] a:visited {
    color: var(--warning) !important;
}

/* --- Markdown general --- */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
}
.stMarkdown p {
    color: var(--text-primary) !important;
    line-height: 1.7 !important;
}
.stMarkdown a {
    color: var(--accent) !important;
    text-decoration: none !important;
    transition: opacity var(--transition) !important;
}
.stMarkdown a:hover {
    opacity: 0.8 !important;
    text-decoration: underline !important;
}
.stMarkdown ul, .stMarkdown ol {
    color: var(--text-primary) !important;
}

/* --- Scrollbar — thin, dark, minimal --- */
* {
    scrollbar-width: thin !important;
    scrollbar-color: var(--bg-hover) transparent !important;
}
*::-webkit-scrollbar {
    width: 5px !important;
    height: 5px !important;
}
*::-webkit-scrollbar-track {
    background: transparent !important;
}
*::-webkit-scrollbar-thumb {
    background-color: var(--bg-hover) !important;
    border-radius: 99px !important;
}
*::-webkit-scrollbar-thumb:hover {
    background-color: var(--text-muted) !important;
}

/* --- Caption / helper text --- */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
}

/* --- Glassmorphism: top-level chat container --- */
[data-testid="stChatMessageContainer"],
section.main > div > div > div[data-testid="stVerticalBlock"] {
    background: transparent !important;
}

/* Subtle glass card on the main messages pane */
.stChatFloatingInputContainer {
    background: linear-gradient(
        to top,
        rgba(13, 17, 23, 0.95) 70%,
        rgba(13, 17, 23, 0.0) 100%
    ) !important;
    backdrop-filter: blur(6px) !important;
    padding-top: 1.5rem !important;
}

/* --- Spinner / processing indicator --- */
.stSpinner > div {
    border-color: var(--accent) transparent transparent transparent !important;
}
.stSpinner p {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    animation: pulse-text 1.5s ease-in-out infinite !important;
}
@keyframes pulse-text {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}

/* ---- Smooth scroll ---- */
html, [data-testid="stChatMessageContainer"], .main .block-container {
    scroll-behavior: smooth !important;
}

/* ---- Chat message line-height and paragraph spacing ---- */
[data-testid="stChatMessageContent"] {
    line-height: 1.7 !important;
}
[data-testid="stChatMessageContent"] p {
    line-height: 1.7 !important;
    margin-bottom: 0.75rem !important;
}
[data-testid="stChatMessageContent"] p:last-child {
    margin-bottom: 0 !important;
}
[data-testid="stChatMessageContent"] pre,
[data-testid="stChatMessageContent"] code {
    line-height: 1.5 !important;
}
[data-testid="stChatMessage"] {
    margin-bottom: 0.75rem !important;
}

/* ---- Diff syntax: green additions, red deletions ---- */
.stCodeBlock .token.inserted,
.language-diff .token.inserted {
    background-color: rgba(63, 185, 80, 0.12) !important;
    display: block !important;
    width: 100% !important;
    border-left: 3px solid var(--success) !important;
    padding-left: 0.4em !important;
    margin-left: -0.4em !important;
}
.stCodeBlock .token.deleted,
.language-diff .token.deleted {
    background-color: rgba(248, 81, 73, 0.12) !important;
    display: block !important;
    width: 100% !important;
    border-left: 3px solid var(--error) !important;
    padding-left: 0.4em !important;
    margin-left: -0.4em !important;
}

/* ---- Expander refinements ---- */
[data-testid="stExpander"] {
    margin-bottom: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.88rem !important;
}

/* ---- Sidebar header: project name + model badge ---- */
.sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 1rem 0;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 1rem;
}
.sidebar-project-name {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}
.sidebar-model-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.6rem;
    background: var(--accent-dim);
    border: 1px solid var(--user-bubble-border);
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--accent) !important;
    white-space: nowrap;
    letter-spacing: 0.01em;
    font-family: var(--font-mono);
}

/* ---- Experimental notice (de-emphasised) ---- */
.experimental-notice {
    font-size: 0.75rem !important;
    color: var(--text-muted) !important;
    margin-top: 1.5rem !important;
    line-height: 1.5 !important;
}
.experimental-notice a {
    color: var(--text-secondary) !important;
    text-decoration: underline !important;
    text-decoration-color: var(--border) !important;
}
.experimental-notice a:hover {
    color: var(--accent) !important;
}

/* ---- Markdown paragraph spacing ---- */
.stMarkdown p {
    margin-bottom: 0.75rem !important;
}

/* ============================================================
   COMMIT CARD — git commit visualization
   ============================================================ */
.commit-card {
    background-color: var(--bg-surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--success);
    border-radius: var(--radius-md);
    padding: 0.65rem 0.9rem;
    margin: 0.5rem 0;
    font-family: var(--font-sans);
}
.commit-card-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
}
.commit-hash-badge {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--success);
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.3);
    border-radius: 99px;
    padding: 0.15rem 0.55rem;
    white-space: nowrap;
    letter-spacing: 0.02em;
    flex-shrink: 0;
}
.commit-message {
    font-size: 0.88rem;
    color: var(--text-primary);
    font-weight: 500;
    line-height: 1.4;
    flex: 1;
}
.commit-file-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.4rem;
}
.commit-file-tag {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-secondary);
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0.1rem 0.45rem;
    white-space: nowrap;
    cursor: default;
}
.commit-file-tag:hover {
    color: var(--accent);
    border-color: var(--user-bubble-border);
    background: var(--accent-dim);
}

/* ============================================================
   SKILLS QUEUE — sidebar skill badge strip
   ============================================================ */
.skill-queue-indicator {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    align-items: center;
    margin-top: 0.4rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.6;
}
.skill-queue-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.5rem;
    background: rgba(88, 166, 255, 0.08);
    border: 1px solid rgba(88, 166, 255, 0.3);
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--accent);
    font-family: var(--font-mono);
    white-space: nowrap;
    letter-spacing: 0.01em;
}
</style>
        """,
        unsafe_allow_html=True,
    )


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

    inject_custom_css()
    inject_generative_background()

    # config_options = st.config._config_options
    # for key, value in config_options.items():
    #    print(f"{key}: {value.value}")

    GUI()


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
