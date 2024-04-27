#!/usr/bin/env python

import os
import random
import sys

import streamlit as st

from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.main import main as cli_main

MESSAGES = [
    "write a python program that shows off some python features",
    "write a tsx program that shows off some language features",
    "refactor the Frobulator.simplify method to be a stand alone function",
    "lorem ipsum dolor",
    "lorem adipiscing adipiscing et dolore sit elit aliqua dolore ut incididunt",
    (
        "sed magna consectetur et quis do magna labore ad elit et elit ad eiusmod sed"
        " labore aliqua eiusmod enim ad nostrud\n\namet consectetur magna tempor do enim"
        " aliqua enim tempor adipiscing sit et"
    ),
]


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
    return coder


class GUI:
    def announce(self):
        lines = self.coder.get_announcements()
        lines = "  \n".join(lines)
        st.info(lines)

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
            prefix = "aider: "
            if commit_message.startswith(prefix):
                commit_message = commit_message[len(prefix) :]
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
        if self.last_undo_button:
            self.last_undo_button.empty()

        self.last_undo_button = st.empty()
        with self.last_undo_button:
            self.button(f"Undo commit `{commit_hash}`", key=f"undo_{commit_hash}")

    def do_sidebar(self):
        with st.sidebar:
            st.title("Aider")
            self.cmds_tab, self.settings_tab = st.tabs(["Commands", "Settings"])

    def do_cmd_tab(self):
        with self.cmds_tab:
            # self.do_recommended_actions()
            self.do_add_to_chat()
            self.do_tokens_and_cost()
            self.do_git()
            self.do_recent_msgs()

    def do_recommended_actions(self):
        with st.expander("Recommended actions", expanded=True):
            with st.popover("Create a git repo to track changes"):
                st.write(
                    "Aider works best when your code is stored in a git repo.  \n[See the FAQ"
                    " for more info](https://aider.chat/docs/faq.html#how-does-aider-use-git)"
                )
                self.button("Create git repo", key=random.random(), help="?")

            with st.popover("Update your `.gitignore` file"):
                st.write("It's best to keep aider's internal files out of your git repo.")
                self.button("Add `.aider*` to `.gitignore`", key=random.random(), help="?")

    def do_add_to_chat(self):
        with st.expander("Add to the chat", expanded=True):
            fnames = st.multiselect(
                "Files for the LLM to edit",
                sorted(self.coder.get_all_relative_files()),
                default=sorted(self.coder.get_inchat_relative_files()),
                placeholder="Files to edit",
                disabled=self.prompt_pending(),
                help=(
                    "Only add the files that need to be *edited* for the task you are working"
                    " on. Aider will pull in other code to provide relevant context to the LLM."
                ),
            )

            for fname in fnames:
                if fname not in self.coder.get_inchat_relative_files():
                    self.coder.add_rel_fname(fname)
                    self.messages.info(f"Added {fname} to the chat")
            for fname in self.coder.get_inchat_relative_files():
                if fname not in fnames:
                    abs_fname = self.coder.abs_root_path(fname)
                    self.coder.abs_fnames.remove(abs_fname)
                    self.messages.info(f"Removed {fname} from the chat")

            with st.popover("Add web page"):
                st.markdown("www")
                st.text_input("URL?")
            with st.popover("Add image"):
                st.markdown("Hello World 👋")
                st.file_uploader("Image file", disabled=self.prompt_pending())
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
                        (
                            "Automatically share the output on non-zero exit code (ie, if any"
                            " tests fail)"
                        ),
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
            with st.popover("Show token usage"):
                st.write("hi")
            if self.button("Clear chat history"):
                self.coder.done_messages = []
                self.coder.cur_messages = []
                self.info("Cleared chat history")

            # st.metric("Cost of last message send & reply", "$0.0019", help="foo")
            # st.metric("Cost to send next message", "$0.0013", help="foo")
            # st.metric("Total cost this session", "$0.22")

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
                "Resend recent chat message",
                MESSAGES,
                placeholder="Choose a recent chat message",
                # label_visibility="collapsed",
                index=None,
                key=f"recent_msgs_{self.state.recent_msgs_num}",
                disabled=self.prompt_pending(),
            )

    def do_messages_container(self):
        self.messages = st.container()

        # stuff a bunch of vertical whitespace at the top
        # to get all the chat text to the bottom
        self.messages.container(height=300, border=False)
        with self.messages:
            self.announce()

            for msg in self.state.messages:
                dump(msg)

                role = msg["role"]

                if role == "edit":
                    self.show_edit_info(msg)
                elif role == "info":
                    st.info(msg["message"])
                elif role in ("user", "assistant"):
                    with st.chat_message(role):
                        st.write(msg["content"])
                        # self.cost()
                else:
                    st.dict(msg)

    def initialize_state(self):
        messages = [{"role": "assistant", "content": "How can I help you?"}]
        self.state.init("messages", messages)
        self.state.init("last_aider_commit_hash", self.coder.last_aider_commit_hash)
        self.state.init("recent_msgs_num", 0)
        self.state.init("prompt")

        dump(self.state.messages)

    def button(self, args, **kwargs):
        "Create a button, disabled if prompt pending"
        kwargs["disabled"] = self.prompt_pending()
        return st.button(args, **kwargs)

    def __init__(self, coder, state):
        self.coder = coder
        self.state = state

        self.last_undo_button = None
        self.recent_msgs_empty = None

        # Force the coder to cooperate, regardless of cmd line args
        self.coder.yield_stream = True
        self.coder.stream = True
        self.coder.io.yes = True
        self.coder.pretty = False

        self.initialize_state()

        self.do_messages_container()
        self.do_sidebar()
        self.do_cmd_tab()

        prompt = st.chat_input("Say something")

        if self.prompt_pending():
            self.process_chat()

        prompt = prompt if prompt else self.old_prompt
        if not prompt:
            return

        self.state.prompt = prompt

        self.coder.io.add_to_input_history(prompt)

        self.state.messages.append({"role": "user", "content": prompt})
        with self.messages.chat_message("user"):
            st.write(prompt)

        # re-render the UI for the prompt_pending state
        st.experimental_rerun()

    def prompt_pending(self):
        return self.state.prompt is not None

    def cost(self):
        cost = random.random() * 0.003 + 0.001
        st.caption(f"${cost:0.4f}")

    def process_chat(self):
        prompt = self.state.prompt
        self.state.prompt = None

        while prompt:
            with self.messages.chat_message("assistant"):
                res = st.write_stream(self.coder.run_stream(prompt))
                self.state.messages.append({"role": "assistant", "content": res})
                # self.cost()
            if self.coder.reflected_message:
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
        st.experimental_rerun()

    def info(self, message):
        info = dict(role="info", message=message)
        self.state.messages.append(info)
        self.messages.info(message)


def gui_main():
    coder = get_coder()
    state = get_state()
    GUI(coder, state)


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
