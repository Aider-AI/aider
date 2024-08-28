#!/usr/bin/env python

import os
import warnings
from pathlib import Path
from typing import List, Optional

import importlib_resources
from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from aider import __version__, utils
from aider.dump import dump  # noqa: F401
from aider.help_pats import exclude_website_pats

warnings.simplefilter("ignore", category=FutureWarning)


def install_help_extra(io) -> bool:
    pip_install_cmd = [
        "aider-chat[help]",
        "--extra-index-url",
        "https://download.pytorch.org/whl/cpu",
    ]
    return utils.check_pip_install_extra(
        io,
        "llama_index.embeddings.huggingface",
        "To use interactive /help you need to install the help extras",
        pip_install_cmd,
    )


def get_package_files() -> List[Path]:
    for path in importlib_resources.files("aider.website").iterdir():
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from path.rglob("*.md")


def fname_to_url(filepath: str) -> str:
    website = "website/"
    index = "/index.md"
    md = ".md"

    docid = ""
    if filepath.startswith("website/_includes/"):
        pass
    elif filepath.startswith(website):
        docid = filepath[len(website):]
        if filepath.endswith(index):
            filepath = filepath[:-len(index)] + "/"
        elif filepath.endswith(md):
            filepath = filepath[:-len(md)] + ".html"
        docid = f"https://aider.chat/{filepath}"

    return docid


def get_index() -> VectorStoreIndex:
    dname = Path.home() / ".aider" / "caches" / f"help.{__version__}"

    if dname.exists():
        storage_context = StorageContext.from_defaults(persist_dir=dname)
        return load_index_from_storage(storage_context)
    
    parser = MarkdownNodeParser()
    nodes = []
    for fname in get_package_files():
        fname = Path(fname)
        if any(fname.match(pat) for pat in exclude_website_pats):
            continue

        doc = Document(
            text=importlib_resources.files("aider.website").joinpath(fname).read_text(encoding="utf-8"),
            metadata=dict(
                filename=fname.name,
                extension=fname.suffix,
                url=fname_to_url(str(fname)),
            ),
        )
        nodes.extend(parser.get_nodes_from_documents([doc]))

    index = VectorStoreIndex(nodes, show_progress=True)
    dname.parent.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(dname)

    return index


class Help:
    def __init__(self):
        from llama_index.core import Settings

        os.environ["TOKENIZERS_PARALLELISM"] = "true"
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        index = get_index()
        self.retriever = index.as_retriever(similarity_top_k=20)

    def ask(self, question: str) -> str:
        nodes = self.retriever.retrieve(question)

        context = f"# Question: {question}\n\n# Relevant docs:\n\n"

        for node in nodes:
            url = node.metadata.get("url", "")
            url_attr = f' from_url="{url}"' if url else ''
            context += f"<doc{url_attr}>\n{node.text}\n</doc>\n\n"

        return context
