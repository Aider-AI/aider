import colorsys
import json
import os
import random

# import shelve
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

import networkx as nx
import tiktoken
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound

from aider import prompts

from .dump import dump  # noqa: F402


def to_tree(tags):
    tags = sorted(tags)

    output = ""
    last = [None] * len(tags[0])
    tab = "\t"
    for tag in tags:
        tag = list(tag)

        for i in range(len(last)):
            if last[i] != tag[i]:
                break

        num_common = i
        indent = tab * num_common
        rest = tag[num_common:]
        for item in rest:
            output += indent + item + "\n"
            indent += tab
        last = tag

    return output


def fname_to_components(fname, with_colon):
    path_components = fname.split(os.sep)
    res = [pc + os.sep for pc in path_components[:-1]]
    if with_colon:
        res.append(path_components[-1] + ":")
    else:
        res.append(path_components[-1])
    return res


class RepoMap:
    ctags_cmd = ["ctags", "--fields=+S", "--extras=-F", "--output-format=json"]
    IDENT_CACHE_FILE = ".aider.ident.cache"
    TAGS_CACHE_FILE = ".aider.tags.cache"

    def __init__(self, use_ctags=None, root=None, main_model="gpt-4", io=None):
        self.io = io

        if not root:
            root = os.getcwd()
        self.root = root

        self.load_ident_cache()
        self.load_tags_cache()

        if use_ctags is None:
            self.use_ctags = self.check_for_ctags()
        else:
            self.use_ctags = use_ctags

        self.tokenizer = tiktoken.encoding_for_model(main_model)

    def get_repo_map(self, chat_files, other_files):
        res = self.choose_files_listing(other_files)
        if not res:
            return

        files_listing, ctags_msg = res

        if chat_files:
            other = "other "
        else:
            other = ""

        repo_content = prompts.repo_content_prefix.format(
            other=other,
            ctags_msg=ctags_msg,
        )
        repo_content += files_listing

        return repo_content

    def choose_files_listing(self, other_files):
        # 1/4 of gpt-4's context window
        max_map_tokens = 2048

        if not other_files:
            return

        if self.use_ctags:
            files_listing = self.get_tags_map(other_files)
            num_tokens = self.token_count(files_listing)
            if self.io:
                self.io.tool_output(f"ctags map: {num_tokens/1024:.1f} k-tokens")
            if num_tokens < max_map_tokens:
                ctags_msg = " with selected ctags info"
                return files_listing, ctags_msg

        files_listing = self.get_simple_files_map(other_files)
        ctags_msg = ""
        num_tokens = self.token_count(files_listing)
        if self.io:
            self.io.tool_output(f"simple map: {num_tokens/1024:.1f} k-tokens")
        if num_tokens < max_map_tokens:
            return files_listing, ctags_msg

    def get_simple_files_map(self, other_files):
        fnames = []
        for fname in other_files:
            fname = self.get_rel_fname(fname)
            fname = fname_to_components(fname, False)
            fnames.append(fname)

        return to_tree(fnames)

    def token_count(self, string):
        return len(self.tokenizer.encode(string))

    def get_rel_fname(self, fname):
        return os.path.relpath(fname, self.root)

    def get_tags_map(self, filenames):
        tags = []
        for filename in filenames:
            if filename.endswith(".md") or filename.endswith(".json"):
                tags.append(self.split_path(filename))
                continue
            tags += self.get_tags(filename, filenames)
        if not tags:
            return

        return to_tree(tags)

    def split_path(self, path):
        path = os.path.relpath(path, self.root)
        return [path + ":"]

    def run_ctags(self, filename):
        # Check if the file is in the cache and if the modification time has not changed
        file_mtime = os.path.getmtime(filename)
        cache_key = filename
        if cache_key in self.TAGS_CACHE and self.TAGS_CACHE[cache_key]["mtime"] == file_mtime:
            return self.TAGS_CACHE[cache_key]["data"]

        cmd = self.ctags_cmd + [filename]
        output = subprocess.check_output(cmd).decode("utf-8")
        output = output.splitlines()

        data = [json.loads(line) for line in output]

        # Update the cache
        self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
        self.save_tags_cache()
        return data

    def get_tags(self, filename, files=None):
        if not files:
            files = set()

        external_references = set()
        other_files = files - set([filename])
        for other_file in other_files:
            external_references.update(self.get_name_identifiers(other_file))

        data = self.run_ctags(filename)

        tags = []

        if not data:
            tags.append(self.split_path(filename))

        for tag in data:
            path = tag.get("path")
            scope = tag.get("scope")
            kind = tag.get("kind")
            name = tag.get("name")
            signature = tag.get("signature")

            if name not in external_references:
                continue

            last = name
            if signature:
                last += " " + signature

            res = self.split_path(path)
            if scope:
                res.append(scope)
            res += [kind, last]
            tags.append(res)

        return tags

    def check_for_ctags(self):
        try:
            with tempfile.TemporaryDirectory() as tempdir:
                hello_py = os.path.join(tempdir, "hello.py")
                with open(hello_py, "w") as f:
                    f.write("def hello():\n    print('Hello, world!')\n")
                self.get_tags(hello_py)
        except Exception:
            return False
        return True

    def load_tags_cache(self):
        self.TAGS_CACHE = dict()  # shelve.open(self.TAGS_CACHE_FILE)

    def save_tags_cache(self):
        # self.TAGS_CACHE.sync()
        pass

    def load_ident_cache(self):
        self.IDENT_CACHE = dict()  # shelve.open(self.IDENT_CACHE_FILE)

    def save_ident_cache(self):
        # self.IDENT_CACHE.sync()
        pass

    def get_name_identifiers(self, fname, uniq=True):
        file_mtime = os.path.getmtime(fname)
        cache_key = fname
        if cache_key in self.IDENT_CACHE and self.IDENT_CACHE[cache_key]["mtime"] == file_mtime:
            idents = self.IDENT_CACHE[cache_key]["data"]
        else:
            idents = self.get_name_identifiers_uncached(fname)
            self.IDENT_CACHE[cache_key] = {"mtime": file_mtime, "data": idents}
            self.save_ident_cache()

        if uniq:
            idents = set(idents)
        return idents

    def get_name_identifiers_uncached(self, fname):
        try:
            with open(fname, "r") as f:
                content = f.read()
        except UnicodeDecodeError:
            return list()

        try:
            lexer = guess_lexer_for_filename(fname, content)
        except ClassNotFound:
            return list()

        # lexer.get_tokens_unprocessed() returns (char position in file, token type, token string)
        tokens = list(lexer.get_tokens_unprocessed(content))
        res = [token[2] for token in tokens if token[1] in Token.Name]
        return res


def find_py_files(directory):
    if not os.path.isdir(directory):
        return [directory]

    py_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files


def get_random_color():
    hue = random.random()
    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 0.75)]
    res = f"#{r:02x}{g:02x}{b:02x}"
    return res


def call_map():
    import graphviz

    fnames = sys.argv[1:]

    fnames = []
    for dname in sys.argv[1:]:
        fnames += find_py_files(dname)

    fnames = sorted(fnames)

    rm = RepoMap()

    # res = rm.get_tags_map(fnames)
    # print(res)

    defines = defaultdict(set)
    references = defaultdict(list)

    root = os.path.commonpath(fnames)

    personalization = dict()

    show_fnames = set()
    for fname in sorted(fnames):
        dump(fname)
        show_fname = os.path.relpath(fname, root)
        show_fnames.add(show_fname)

        if ".venv" not in show_fname:
            personalization[show_fname] = 1.0

        data = rm.run_ctags(fname)

        for tag in data:
            ident = tag["name"]
            defines[ident].add(show_fname)
            # dump("def", fname, ident)

        idents = rm.get_name_identifiers(fname, uniq=False)
        for ident in idents:
            # dump("ref", fname, ident)
            references[ident].append(show_fname)

    idents = set(defines.keys()).intersection(set(references.keys()))

    G = nx.MultiDiGraph()

    for ident in idents:
        definers = defines[ident]
        num_defs = len(definers)
        # if num_defs > 3:
        #    continue

        for referencer, num_refs in Counter(references[ident]).items():
            for definer in definers:
                if referencer == definer:
                    continue
                weight = num_refs / num_defs
                G.add_edge(referencer, definer, weight=num_refs, ident=ident)

    # personalization = dict()
    # personalization["utils.py"] = 1.0

    ranked = nx.pagerank(
        G,
        weight="weight",
        personalization=personalization,
        dangling=personalization,
    )

    # distribute the rank from each source node, across all of its out edges
    ranked_definitions = defaultdict(float)
    for src in G.nodes:
        src_rank = ranked[src]
        total_weight = sum(data["weight"] for _src, _dst, data in G.out_edges(src, data=True))
        dump(src, src_rank, total_weight)
        for src, dst, data in G.out_edges(src, data=True):
            data["rank"] = data["weight"] / total_weight * src_rank
            ident = data["ident"]
            ranked_definitions[(dst, ident)] += data["rank"]

    ranked_definitions = sorted(ranked_definitions.items(), reverse=True, key=lambda x: x[1])
    for (fname, ident), rank in ranked_definitions:
        print(f"{rank:.03f} {fname} {ident}")

    return
    #############

    N = 20
    top_10_nodes = sorted(ranked, key=ranked.get, reverse=True)[:N]
    nodes_to_remove = [node for node in G.nodes if node not in top_10_nodes]
    G.remove_nodes_from(nodes_to_remove)

    """
    # drop low weight edges for plotting
    edges_to_remove = [
        (node1, node2) for node1, node2, data in G.edges(data=True) if data["weight"] < 1
    ]
    G.remove_edges_from(edges_to_remove)
    # Remove isolated nodes (nodes with no edges)
    G.remove_nodes_from(list(nx.isolates(G)))
    """

    dot = graphviz.Digraph(graph_attr={"ratio": ".5"})

    max_rank = max(ranked.values())
    min_rank = min(ranked.values())
    for fname in G.nodes():
        fname = str(fname)
        rank = ranked[fname]
        size = (rank - min_rank) / (max_rank - min_rank)
        pen = max(10 * size, 1)
        size = 2 * size
        fontsize = max(10 * size, 14)
        dot.node(
            fname, penwidth=str(pen), width=str(size), height=str(size), fontsize=str(fontsize)
        )

    for refs, defs, data in G.edges(data=True):
        weight = data["weight"]
        label = data["ident"]

        color = get_random_color()
        weight = weight
        dot.edge(refs, defs, penwidth=str(weight), color=color, fontcolor=color, label=label)

    top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
    # Print the PageRank of each node
    for rank, node in top_rank[:N]:
        print(f"{rank:.03f} {node}")

    # dot.render("tmp", format="pdf", view=True)


if __name__ == "__main__":
    call_map()
    # print(rm.get_tags_map(sys.argv[1:]))
