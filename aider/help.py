#!/usr/bin/env python

import os
import warnings
from pathlib import Path

import importlib_resources

from aider import __version__, utils
from aider.dump import dump  # noqa: F401
from aider.help_pats import exclude_website_pats

warnings.simplefilter("ignore", category=FutureWarning)


def get_package_files():
    for path in importlib_resources.files("aider.website").iterdir():
        if path.is_file():
            yield path
        elif path.is_dir():
            for subpath in path.rglob("*.md"):
                yield subpath


def fname_to_url(filepath):
    website = "website/"
    index = "/index.md"
    md = ".md"

    docid = ""
    if filepath.startswith("website/_includes/"):
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

    dname = Path.home() / ".aider" / "caches" / ("help." + __version__)

    if dname.exists():
        storage_context = StorageContext.from_defaults(
            persist_dir=dname,
        )
        index = load_index_from_storage(storage_context)
    else:
        parser = MarkdownNodeParser()

        nodes = []
        for fname in get_package_files():
            fname = Path(fname)
            if any(fname.match(pat) for pat in exclude_website_pats):
                continue

            doc = Document(
                text=importlib_resources.files("aider.website")
                .joinpath(fname)
                .read_text(encoding="utf-8"),
                metadata=dict(
                    filename=fname.name,
                    extension=fname.suffix,
                    url=fname_to_url(str(fname)),
                ),
            )
            nodes += parser.get_nodes_from_documents([doc])

        index = VectorStoreIndex(nodes, show_progress=True)
        dname.parent.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(dname)

    return index


class PipInstallHF(Exception):
    pass


pip_install_cmd = [
    "aider-chat[hf-embed]",
    "--extra-index-url",
    "https://download.pytorch.org/whl/cpu",
]

pip_install_error = f"""
To use interactive /help you need to install HuggingFace embeddings:

pip install {' '.join(pip_install_cmd)}

"""  # noqa: E231


class Help:
    def __init__(self, pip_install=False):
        if pip_install:
            utils.pip_install(pip_install_cmd)

        try:
            from llama_index.core import Settings
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError:
            raise PipInstallHF(pip_install_error)

        os.environ["TOKENIZERS_PARALLELISM"] = "true"
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        index = get_index()

        self.retriever = index.as_retriever(similarity_top_k=20)

    def ask(self, question):
        nodes = self.retriever.retrieve(question)

        context = f"""# Question: {question}

# Relevant docs:

"""  # noqa: E231

        for node in nodes:
            url = node.metadata.get("url", "")
            if url:
                url = f' from_url="{url}"'

            context += f"<doc{url}>\n"
            context += node.text
            context += "\n</doc>\n\n"

        return context
