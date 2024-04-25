#!/usr/bin/env python

import os
import sys
from pathlib import Path
from collections import defaultdict

from aider.dump import dump

import streamlit as st

from aider.dump import dump
from aider.coders import Coder
from aider.models import Model

from streamlit_file_browser import st_file_browser
from streamlit_searchbox import st_searchbox
from st_row_buttons import st_row_buttons


if 'recent_msgs_num' not in st.session_state:
    st.session_state.recent_msgs_num = 0

recent_msgs_label = "Recent chat messages"
def recent_msgs():
    msgs = [
        "write a python program that shows off some python features",
        "write a tsx program that shows off some language features",
        "refactor the Frobulator.simplify method to be a stand alone function",
        "lorem ipsum dolor",
        "lorem adipiscing adipiscing et dolore sit elit aliqua dolore ut incididunt",
        "sed magna consectetur et quis do magna labore ad elit et elit ad eiusmod sed labore aliqua eiusmod enim ad nostrud\n\namet consectetur magna tempor do enim aliqua enim tempor adipiscing sit et"
    ]
    msgs = 30 * msgs

    return st.selectbox(
        recent_msgs_label,
        msgs,
        placeholder = "Recent chat messages",
        label_visibility = "collapsed",
        index = None,
        key=f"recent_msgs_{st.session_state.recent_msgs_num}",
    )


def search(text=None):
    results = []
    for root, _, files in os.walk("aider"):
        for file in files:
            path = os.path.join(root, file)
            if not text or text in path:
                results.append(path)
    #dump(results)

    return results

#selected_value = st_searchbox(search)


model = Model("gpt-3.5-turbo", weak_model="gpt-3.5-turbo")
fnames = ["greeting.py"]
coder = Coder.create(main_model=model, fnames=fnames, use_git=False)

import random

lorem_words = [
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
    "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
    "incididunt", "ut", "labore", "et", "dolore", "magna",
    "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud"
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
    "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
    "incididunt", "ut", "labore", "et", "dolore", "magna",
    "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud"
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
    "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
    "incididunt", "ut", "labore", "et", "dolore", "magna",
    "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud"
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
    "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
    "incididunt", "ut", "labore", "et", "dolore", "magna",
    "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud"
    "\n\n",
    "\n\n",
    "\n\n",
]

def generate_lorem_text(min_words=10, max_words=50):
    num_words = random.randint(min_words, max_words)
    words = random.sample(lorem_words, num_words)
    return " ".join(words)

with st.sidebar:
    st.header("Aider")

    cmds_tab, settings_tab = st.tabs(["Commands", "Settings"])

with cmds_tab:
    with st.expander("Add to the chat", expanded=True):
        st.multiselect(
            "Files for the LLM to edit",
            search(),
            default=["aider/main.py","aider/io.py"],
            help="Only add the files that need to be *edited* for the task you are working in. Aider will pull in other code to provide relevant context to the LLM.",
        )
        with st.popover("Add web page"):
            st.markdown("www")
            name = st.text_input("URL?")
        with st.popover("Add image"):
            st.markdown("Hello World 👋")
            st.file_uploader("Image file")
        with st.popover("Run shell command"):
            st.markdown("## Run a shell command and share the output with aider")
            name = st.text_input("Cmd")
            st.selectbox("Recent commands", [
                "my_app.py --doit",
                "my_app.py --cleanup",
            ])

        with st.popover("Run test command"):
            st.markdown("Hello World 👋")
            name = st.text_input("Test")

    with st.expander("Costs and context", expanded=True):
        st.button("Show token usage")
        st.button("Clear chat history")
        st.metric("Per message context cost", "$0.0013", help="foo")
        st.metric("Total cost this session", "$0.22")


    with st.expander("Git", expanded=True):
        st.button("Show last diff")
        st.button("Undo last commit")
        st.button("Commit pending changes")
        with st.popover("Run git command"):
            st.markdown("## Run git command")
            name = st.text_input("git", value="git ")
            st.button("Run")
            st.selectbox("Recent git commands", [
                "git checkout -b experiment",
                "git stash",
            ])



#chat_tab, settings_tab = st.tabs(["Chat", "Settings"])


messages = st.container()
messages.container(height = 1200, border=False)
recent_msgs_empty = st.empty()

with recent_msgs_empty:
    old_prompt = recent_msgs()

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]


for msg in st.session_state.messages:
    messages.chat_message(msg["role"]).write(msg["content"])

_='''
with st.expander("Commands"):
    st.markdown("## Run git command")
    name = st.text_input("gitx", value="git ")
    st.button("Run it")
    st.selectbox("Recent chat commands", [
        "git checkout -b experiment",
        "git stash",
    ])
'''


prompt = st.chat_input("Say something")
dump(old_prompt, prompt)

if old_prompt:
    prompt = old_prompt
    st.session_state.recent_msgs_num += 1
    with recent_msgs_empty:
        old_prompt = recent_msgs()

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})
    with messages.chat_message("user"):
        st.write(prompt)

    res = coder.run(prompt)
    st.session_state.messages.append({"role": "assistant", "content": res})

    with messages.chat_message("ai"):
        st.write(res)
