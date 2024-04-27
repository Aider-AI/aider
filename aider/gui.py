#!/usr/bin/env python

import os
import random
import sys
from pathlib import Path

import streamlit as st

from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.main import main as cli_main


# st.cache_data
def get_diff():
    return Path("/Users/gauthier/Projects/aider/aider/tmp.diff").read_text()


diff = get_diff()


def recent_msgs():
    msgs = [
        "write a python program that shows off some python features",
        "write a tsx program that shows off some language features",
        "refactor the Frobulator.simplify method to be a stand alone function",
        "lorem ipsum dolor",
        "lorem adipiscing adipiscing et dolore sit elit aliqua dolore ut incididunt",
        (
            "sed magna consectetur et quis do magna labore ad elit et elit ad eiusmod sed labore"
            " aliqua eiusmod enim ad nostrud\n\namet consectetur magna tempor do enim aliqua enim"
            " tempor adipiscing sit et"
        ),
    ]
    # msgs = 30 * msgs

    return st.selectbox(
        "N/A",
        msgs,
        placeholder="Resend recent chat message",
        label_visibility="collapsed",
        index=None,
        key=f"recent_msgs_{st.session_state.recent_msgs_num}",
    )


def search(text=None):
    results = []
    for root, _, files in os.walk("aider"):
        for file in files:
            path = os.path.join(root, file)
            if not text or text in path:
                results.append(path)
    # dump(results)

    return results


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

        if len(fnames) == 1:
            res += f"Applied edits to `{fnames[0]}`"
        elif len(fnames) > 1:
            res += "Applied edits to:  \n"
            for fname in fnames:
                res += f"- `{fname}`  \n"

        with st.container(border=True):
            st.write(res)
            if show_undo:
                st.button(f"Undo commit `{commit_hash}`", key=f"undo_{commit_hash}")

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
                st.button("Create git repo", key=random.random(), help="?")

            with st.popover("Update your `.gitignore` file"):
                st.write("It's best to keep aider's internal files out of your git repo.")
                st.button("Add `.aider*` to `.gitignore`", key=random.random(), help="?")

    def do_add_to_chat(self):
        with st.expander("Add to the chat", expanded=True):
            fnames = st.multiselect(
                "Files for the LLM to edit",
                sorted(self.coder.get_all_relative_files()),
                default=sorted(self.coder.get_inchat_relative_files()),
                placeholder="Files to edit",
                help=(
                    "Only add the files that need to be *edited* for the task you are working"
                    " on. Aider will pull in other code to provide relevant context to the LLM."
                ),
            )

            for fname in fnames:
                if fname not in self.coder.get_inchat_relative_files():
                    self.coder.add_rel_fname(fname)

            with st.popover("Add web page"):
                st.markdown("www")
                st.text_input("URL?")
            with st.popover("Add image"):
                st.markdown("Hello World 👋")
                st.file_uploader("Image file")
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
                )

    def do_tokens_and_cost(self):
        with st.expander("Tokens and costs", expanded=True):
            with st.popover("Show token usage"):
                st.write("hi")
            st.button("Clear chat history")
            # st.metric("Cost of last message send & reply", "$0.0019", help="foo")
            # st.metric("Cost to send next message", "$0.0013", help="foo")
            # st.metric("Total cost this session", "$0.22")

    def do_git(self):
        with st.expander("Git", expanded=False):
            # st.button("Show last diff")
            # st.button("Undo last commit")
            st.button("Commit any pending changes")
            with st.popover("Run git command"):
                st.markdown("## Run git command")
                st.text_input("git", value="git ")
                st.button("Run")
                st.selectbox(
                    "Recent git commands",
                    [
                        "git checkout -b experiment",
                        "git stash",
                    ],
                )

    def do_recent_msgs(self):
        self.recent_msgs_empty = st.empty()
        self.reset_recent_msgs()

    def reset_recent_msgs(self):
        self.recent_msgs_empty.empty()
        with self.recent_msgs_empty:
            self.old_prompt = recent_msgs()

    def do_messages_container(self):
        self.messages = st.container()

        # stuff a bunch of vertical whitespace at the top
        # to get all the chat text to the bottom
        self.messages.container(height=1200, border=False)
        with self.messages:
            self.announce()

            for msg in st.session_state.messages:
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

    def init_state(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

        if "recent_msgs_num" not in st.session_state:
            st.session_state.recent_msgs_num = 0

        if "last_aider_commit_hash" not in st.session_state:
            st.session_state.last_aider_commit_hash = self.coder.last_aider_commit_hash

    def __init__(self, coder):
        self.coder = coder

        # Force the coder to cooperate, regardless of cmd line args
        self.coder.yield_stream = True
        self.coder.stream = True
        self.coder.io.yes = True
        self.coder.pretty = False

        self.init_state()

        self.do_sidebar()
        self.do_cmd_tab()
        self.do_messages_container()

        self.prompt = st.chat_input("Say something")

        if self.prompt:
            self.chat(self.prompt)
            return

        if self.old_prompt:
            prompt = self.old_prompt
            st.session_state.recent_msgs_num += 1
            self.reset_recent_msgs()
            self.chat(prompt)

    def cost(self):
        cost = random.random() * 0.003 + 0.001
        st.caption(f"${cost:0.4f}")

    def chat(self, prompt):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with self.messages.chat_message("user"):
            st.write(prompt)

        while prompt:
            with self.messages.chat_message("assistant"):
                res = st.write_stream(self.coder.run_stream(prompt))
                st.session_state.messages.append({"role": "assistant", "content": res})
                # self.cost()
            if self.coder.reflected_message:
                info = dict(role="info", message=self.coder.reflected_message)
                st.session_state.messages.append(info)
                self.messages.info(self.coder.reflected_message)
            prompt = self.coder.reflected_message

        with self.messages:
            edit = dict(
                role="edit",
                fnames=self.coder.aider_edited_files,
            )
            if st.session_state.last_aider_commit_hash != self.coder.last_aider_commit_hash:
                edit["commit_hash"] = self.coder.last_aider_commit_hash
                edit["commit_message"] = self.coder.last_aider_commit_message
                st.session_state.last_aider_commit_hash = self.coder.last_aider_commit_hash

            st.session_state.messages.append(edit)
            self.show_edit_info(edit)


def gui_main():
    coder = get_coder()
    GUI(coder)


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
