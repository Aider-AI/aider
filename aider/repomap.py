import json
import os
import subprocess
import sys
import tempfile
import json
from collections import Counter, defaultdict

import networkx as nx
import tiktoken
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound

from aider import prompts

# from .dump import dump


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
    TAGS_CACHE_FILE = ".aider.tags.cache"

    def load_tags_cache(self):
        if os.path.exists(self.TAGS_CACHE_FILE):
            with open(self.TAGS_CACHE_FILE, "r") as f:
                self.TAGS_CACHE = json.load(f)
        else:
            self.TAGS_CACHE = dict()

    def save_tags_cache(self):
        with open(self.TAGS_CACHE_FILE, "w") as f:
            json.dump(self.TAGS_CACHE, f)
    TAGS_CACHE = None
    IDENT_CACHE = None

    def __init__(self, use_ctags=None, root=None, main_model="gpt-4"):
        self.load_tags_cache()
        if not root:
            root = os.getcwd()
        self.root = root

        self.TAGS_CACHE = dict()
        self.load_ident_cache()

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
            tokens = self.token_count(files_listing)
            if tokens < max_map_tokens:
                ctags_msg = " with selected ctags info"
                return files_listing, ctags_msg

        files_listing = self.get_simple_files_map(other_files)
        ctags_msg = ""
        if self.token_count(files_listing) < max_map_tokens:
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

    def load_ident_cache(self):
        if os.path.exists(self.IDENT_CACHE_FILE):
            with open(self.IDENT_CACHE_FILE, "r") as f:
                self.IDENT_CACHE = json.load(f)
        else:
            self.IDENT_CACHE = dict()

    def save_ident_cache(self):
        with open(self.IDENT_CACHE_FILE, "w") as f:
            json.dump(self.IDENT_CACHE, f)

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


def call_map():
    import random

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

    show_fnames = set()
    for fname in sorted(fnames):
        from .dump import dump

        dump(fname)
        show_fname = os.path.relpath(fname, root)
        show_fnames.add(show_fname)

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

    dot = graphviz.Digraph(graph_attr={"ratio": ".5"})

    labels = defaultdict(list)
    edges = defaultdict(float)
    for ident in idents:
        defs = defines[ident]
        num_defs = len(defs)
        if num_defs > 3:
            continue

        for referencer, num_refs in Counter(references[ident]).items():
            for definer in defines[ident]:
                if referencer == definer:
                    continue
                # tuple(sorted([referencer, definer]))
                name = referencer, definer
                edges[name] += num_refs / num_defs
                labels[name].append((num_refs, ident))

    G = nx.DiGraph()

    for edge, weight in edges.items():
        refs, defs = edge
        G.add_edge(refs, defs, weight=weight)

    ranked = nx.pagerank(G, weight="weight")

    top_10_nodes = sorted(ranked, key=ranked.get, reverse=True)[:20]
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

    max_w = max(edges.values())
    for refs, defs, data in G.edges(data=True):
        weight = data["weight"]

        r = random.randint(0, 128)
        g = random.randint(0, 128)
        b = random.randint(0, 128)
        color = f"#{r:02x}{g:02x}{b:02x}80"
        weight = weight * 10 / max_w
        label = labels[(refs, defs)]
        label = sorted(label, reverse=True)
        label = " ".join(ident for cnt, ident in label[:5])
        dot.edge(refs, defs, penwidth=str(weight), color=color, label=label, fontcolor=color)

    top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
    # Print the PageRank of each node
    for rank, node in top_rank:
        print(f"{node} rank: {rank}")

    dot.render("tmp", format="pdf", view=True)


if __name__ == "__main__":
    call_map()
    # print(rm.get_tags_map(sys.argv[1:]))
