import os
import json
import sys
import subprocess
import tiktoken
import tempfile
from collections import defaultdict

from aider import prompts, utils
from aider.dump import dump


# Global cache for tags
TAGS_CACHE = {}


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

    def __init__(self, use_ctags=None, root=None, main_model="gpt-4"):
        if not root:
            root = os.getcwd()
        self.root = root

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
            if self.token_count(files_listing) < max_map_tokens:
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
            tags += self.get_tags(filename)
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
        if cache_key in TAGS_CACHE and TAGS_CACHE[cache_key]["mtime"] == file_mtime:
            return TAGS_CACHE[cache_key]["data"]

        cmd = self.ctags_cmd + [filename]
        output = subprocess.check_output(cmd).decode("utf-8")
        output = output.splitlines()

        data = [json.loads(line) for line in output]

        # Update the cache
        TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
        return data

    def get_tags(self, filename):
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

    """
    fnames = []
    for dname in sys.argv[1:]:
        fnames += find_py_files(dname)

    fnames = sorted(fnames)
    """

    rm = RepoMap()

    # res = rm.get_tags_map(fnames)
    # print(res)

    defines = defaultdict(set)
    references = defaultdict(list)

    root = os.path.commonpath(fnames)

    show_fnames = set()
    for fname in fnames:
        show_fname = os.path.relpath(fname, root)
        show_fnames.add(show_fname)

        data = rm.run_ctags(fname)

        for tag in data:
            ident = tag["name"]
            defines[ident].add(show_fname)
            # dump("def", fname, ident)

        idents = utils.get_name_identifiers(fname, uniq=False)
        for ident in idents:
            # dump("ref", fname, ident)
            references[ident].append(show_fname)

    for ident, fname in defines.items():
        dump(fname, ident)

    idents = set(defines.keys()).intersection(set(references.keys()))

    dot = graphviz.Graph()

    labels = defaultdict(list)
    edges = defaultdict(float)
    for ident in idents:
        defs = defines[ident]
        num_defs = len(defs)
        if num_defs > 1:
            continue

        for refs in references[ident]:
            for defs in defines[ident]:
                if refs == defs:
                    continue
                name = tuple(sorted([refs, defs]))
                edges[name] += 1 / num_defs
                labels[name].append(ident)

    import networkx as nx

    G = nx.Graph()

    for edge, weight in edges.items():
        refs, defs = edge
        G.add_edge(refs, defs, weight=weight)

    ranked = nx.pagerank(G, weight="weight")

    # drop low weight edges for plotting
    edges_to_remove = [
        (node1, node2) for node1, node2, data in G.edges(data=True) if data["weight"] < 1
    ]
    G.remove_edges_from(edges_to_remove)
    # Remove isolated nodes (nodes with no edges)
    dump(G.nodes())
    G.remove_nodes_from(list(nx.isolates(G)))
    dump(G.nodes())

    max_rank = max(ranked.values())
    min_rank = min(ranked.values())
    for fname in G.nodes():
        fname = str(fname)
        rank = ranked[fname]
        size = 10 * (rank - min_rank) / (max_rank - min_rank) + 1
        dot.node(fname, penwidth=str(size), width=str(size), height=str(size))

    max_w = max(edges.values())
    for refs, defs, data in G.edges(data=True):
        weight = data["weight"]

        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        color = f"#{r:02x}{g:02x}{b:02x}80"
        weight = weight * 10 / max_w
        dot.edge(refs, defs, penwidth=str(weight), color=color)

        name = tuple(sorted([refs, defs]))
        print()
        print(name)
        for ident in sorted(labels[name]):
            print("\t", ident)
        # print(f"{refs} -{weight}-> {defs}")

    top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
    # Print the PageRank of each node
    for rank, node in top_rank:
        print(f"{node} rank: {rank}")

    dot.render("tmp", format="pdf", view=True)


if __name__ == "__main__":
    call_map()
