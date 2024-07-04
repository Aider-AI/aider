#!/usr/bin/env python

import os
import sys
import warnings
from pathlib import Path

from tqdm import tqdm
import importlib_resources

from aider.dump import dump  # noqa: F401

warnings.simplefilter("ignore", category=FutureWarning)


def get_package_files():
    website_files = importlib_resources.files('website')
    for path in website_files.rglob('*.md'):
        if not any(part.startswith(('OLD', 'tmp')) or part in ('examples', '_posts') for part in path.parts):
            dump(path)
            yield str(path)


def fname_to_url(filepath):
    website = "website/"
    index = "/index.md"
    md = ".md"

    docid = ""
    if filepath.startswith("website/_includes/"):
        pass
    elif "HISTORY.html" in filepath:
        # too much stale info
        pass
    elif filepath.startswith(website):
        docid = filepath[len(website) :]

        if filepath.endswith(index):
            filepath = filepath[: -len(index)] + "/"
        elif filepath.endswith(md):
            filepath = filepath[: -len(md)] + ".html"

        docid = "https://aider.chat/" + filepath

    return docid


def get_index():
    from llama_index.core import (
        Document,
        StorageContext,
        VectorStoreIndex,
        load_index_from_storage,
    )
    from llama_index.core.node_parser import MarkdownNodeParser

    dname = Path.home() / ".aider" / "help"

    if dname.exists():
        storage_context = StorageContext.from_defaults(
            persist_dir=dname,
        )
        index = load_index_from_storage(storage_context)
    else:
        parser = MarkdownNodeParser()

        nodes = []
        for fname in tqdm(list(get_package_files())):
            fname = Path(fname)
            doc = Document(
                text=importlib_resources.files('website').joinpath(fname).read_text(),
                metadata=dict(
                    filename=fname.name,
                    extension=fname.suffix,
                    url=fname_to_url(str(fname)),
                ),
            )
            nodes += parser.get_nodes_from_documents([doc])

        index = VectorStoreIndex(nodes)
        dname.parent.mkdir(exist_ok=True)
        index.storage_context.persist(dname)

    return index


class Help:
    def __init__(self):
        from llama_index.core import Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        os.environ["TOKENIZERS_PARALLELISM"] = "true"
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        index = get_index()

        self.retriever = index.as_retriever(similarity_top_k=20)

    def ask(self, question):
        nodes = self.retriever.retrieve(question)

        context = f"""# Question: {question}

# Relevant docs:

"""

        for node in nodes:
            url = node.metadata.get("url", "")
            if url:
                url = f' from_url="{url}"'

            context += f"<doc{url}>\n"
            context += node.text
            context += "\n</doc>\n\n"

        return context


#
# question = "how can i convert a python script to js"
# question = "i am getting an error message about unknown context window"
# question = "i am getting an error message about exhausted context window"
# question = "The chat session is larger than the context window!"
# question = "how do i add deepseek api key to yaml"
# question = (
#    "It would be great if I could give aider an example github PR and instruct it to do the same"
#    " exact thing for another integration."
# )

question = " ".join(sys.argv[1:])
