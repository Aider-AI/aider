#!/usr/bin/env python

import time
from pathlib import Path

import litellm
from dump import dump
from llama_index.core import (
    Document,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import MarkdownNodeParser

litellm.suppress_debug_info = True


def should_skip_dir(dirname):
    if dirname.startswith("OLD"):
        return True
    if dirname.startswith("tmp"):
        return True
    if dirname == "examples":
        return True
    if dirname == "_posts":
        return True


def walk_subdirs_for_files(root_dir):
    root_path = Path(root_dir)
    for path in root_path.rglob("*.md"):
        if any(should_skip_dir(part) for part in path.parts):
            continue
        yield str(path)


def execute(question, text):
    sys_content = """Answer questions about how to use the Aider program.
Give answers about how to use aider to accomplish the user's questions,
not general advice on how to use other tools or approaches.

Use the provided aider documentation *if it is relevant to the user's questions*.

Include a urls to the aider docs that might be relevant for the user to read
.

If you don't know the answer, say so and suggest some relevant aider doc urls.
If the user asks how to do something that aider doesn't support, tell them that.

Be helpful but concise.

Unless the question indicates otherwise, assume the user wants to use
aider as a CLI tool.
"""

    usage = Path("website/docs/usage.md").read_text()

    content = f"""# Question:

{question}


# Relevant documentation:

{text}

#####

{usage}
"""

    messages = [
        dict(
            role="system",
            content=sys_content,
        ),
        dict(
            role="user",
            content=content,
        ),
    ]

    res = litellm.completion(
        messages=messages,
        # model="gpt-3.5-turbo",
        model="gpt-4o",
    )

    return res


def fname_to_url(filepath):
    if filepath.startswith("website/_includes/"):
        docid = ""
    else:
        website = "website/"
        assert filepath.startswith(website), filepath
        docid = filepath[len(website) :]
        docid = "https://aider.chat/" + filepath

    return docid


def get_index():
    dname = Path("storage")
    if dname.exists():
        storage_context = StorageContext.from_defaults(
            persist_dir=dname,
        )
        index = load_index_from_storage(storage_context)
    else:
        parser = MarkdownNodeParser()

        nodes = []
        for fname in walk_subdirs_for_files("website"):
            dump(fname)
            # doc = FlatReader().load_data(Path(fname))
            fname = Path(fname)
            doc = Document(
                text=fname.read_text(),
                metadata=dict(
                    filename=fname.name,
                    extension=fname.suffix,
                    url=fname_to_url(str(fname)),
                ),
            )
            nodes += parser.get_nodes_from_documents([doc])

        index = VectorStoreIndex(nodes)
        index.storage_context.persist(dname)

    return index


when = time.time()

index = get_index()

print("get_index", time.time() - when)
when = time.time()

retriever = index.as_retriever(similarity_top_k=20)

#
# question = "how can i convert a python script to js"
# question = "i am getting an error message about unknown context window"
# question = "i am getting an error message about exhausted context window"
# question = "The chat session is larger than the context window!"
# question = "how do i add deepseek api key to yaml"
question = (
    "It would be great if I could give aider an example github PR and instruct it to do the same"
    " exact thing for another integration."
)

nodes = retriever.retrieve(question)

print("retrieve", time.time() - when)
when = time.time()

dump(len(nodes))

context = ""
for node in nodes:
    fname = node.metadata["filename"]
    url = node.metadata.get("url", "")
    if url:
        url = f' from_url="{url}"'

    context += f"<doc{url}>\n"
    context += node.text
    context += "\n</doc>\n\n"

# dump(context)

res = execute(question, context)
content = res.choices[0].message.content
dump(content)

print("llm", time.time() - when)
when = time.time()
