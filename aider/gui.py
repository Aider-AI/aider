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

    dump(st.session_state.recent_msgs_num)
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
    if isinstance(coder, Coder):
        return coder
    raise ValueError()


class GUI:
    def announce(self):
        lines = self.coder.get_announcements()
        lines = "  \n".join(lines)
        st.info(lines)

    def mock_tool_output(self):
        messages = """Applied edit to new_program.py"""
        # st.info(messages)

        if self.chat_controls:
            self.chat_controls.empty()

        self.chat_controls = st.empty()
        with self.chat_controls:
            container = st.container()

        with container:
            # cols = st.columns([0.8,0.2])
            # with cols[0]:

            # with st.expander(messages):
            #    diff = Path("aider/tmp.diff").read_text()
            #    st.code(diff, language="diff")
            with st.expander(
                "Commit `33a242c`: Added sample python that highlights language features "
                f" \n{messages}"
            ):
                # st.info(messages)
                st.code(diff, language="diff")
                st.button(
                    "Undo commit `33a242c`",
                    key=random.random(),
                    help="wtf?",
                )

            if False:
                st.button("Allow edits to `foobar.py`", key=random.random(), help="??")
                st.button("Allow creation of new file `some/new/file.js`", key=random.random())
                st.button("Add `baz/foo.py` to the chat", key=random.random())

    def do_sidebar(self):
        with st.sidebar:
            st.title("Aider")
            self.cmds_tab, self.settings_tab = st.tabs(["Commands", "Settings"])

    def do_cmd_tab(self):
        with self.cmds_tab:
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

            with st.expander("Add to the chat", expanded=True):
                st.multiselect(
                    "Files for the LLM to edit",
                    self.coder.get_all_relative_files(),
                    default=self.coder.get_inchat_relative_files(),
                    help=(
                        "Only add the files that need to be *edited* for the task you are working"
                        " on. Aider will pull in other code to provide relevant context to the LLM."
                    ),
                )
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

            with st.expander("Tokens and costs", expanded=True):
                with st.popover("Show token usage"):
                    st.write("hi")
                st.button("Clear chat history")
                # st.metric("Cost of last message send & reply", "$0.0019", help="foo")
                # st.metric("Cost to send next message", "$0.0013", help="foo")
                st.metric("Total cost this session", "$0.22")

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
            with self.messages.chat_message(msg["role"]):
                st.write(msg["content"])
                cost = random.random() * 0.003 + 0.001
                st.caption(f"${cost:0.4f}")

    def clear_controls(self):
        if self.chat_controls:
            self.chat_controls.empty()

    def init_state(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

        if "recent_msgs_num" not in st.session_state:
            st.session_state.recent_msgs_num = 0

    def __init__(self, coder):
        self.coder = coder
        self.chat_controls = None

        self.init_state()

        self.do_sidebar()
        self.do_cmd_tab()
        self.do_messages_container()

        self.prompt = st.chat_input("Say something", on_submit=self.clear_controls)

        if self.prompt:
            self.chat(self.prompt)
            return

        if self.old_prompt:
            prompt = self.old_prompt
            st.session_state.recent_msgs_num += 1
            self.reset_recent_msgs()
            self.chat(prompt)

    def chat(self, prompt):
        self.clear_controls()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with self.messages.chat_message("user"):
            st.write(prompt)

        res = self.coder.run(prompt)
        st.session_state.messages.append({"role": "assistant", "content": res})

        with self.messages.chat_message("assistant"):
            st.write(res)
            cost = random.random() * 0.003 + 0.001
            st.caption(f"${cost:0.4f}")

        with self.messages:
            self.mock_tool_output()


def gui_main():
    coder = get_coder()
    GUI(coder)


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
