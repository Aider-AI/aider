import colorsys
import json
import os
import random
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
from diskcache import Cache
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound
from tqdm import tqdm

from aider import models

from .dump import dump  # noqa: F402


def to_tree(tags):
    if not tags:
        return ""

    tags = sorted(tags)

    output = ""
    last = [None] * len(tags[0])
    tab = "\t"
    for tag in tags:
        tag = list(tag)

        for i in range(len(last) + 1):
            if i == len(last):
                break
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
    CACHE_VERSION = 1
    ctags_cmd = [
        "ctags",
        "--fields=+S",
        "--extras=-F",
        "--output-format=json",
        "--output-encoding=utf-8",
    ]
    IDENT_CACHE_DIR = f".aider.ident.cache.v{CACHE_VERSION}"
    TAGS_CACHE_DIR = f".aider.tags.cache.v{CACHE_VERSION}"

    ctags_disabled_reason = "ctags not initialized"

    cache_missing = False

    def __init__(
        self,
        map_tokens=1024,
        root=None,
        main_model=models.Model.strong_model(),
        io=None,
        repo_content_prefix=None,
        verbose=False,
    ):
        self.io = io
        self.verbose = verbose

        if not root:
            root = os.getcwd()
        self.root = root

        self.load_ident_cache()
        self.load_tags_cache()

        self.max_map_tokens = map_tokens
        self.has_ctags = self.check_for_ctags()

        if map_tokens > 0 and self.has_ctags:
            self.use_ctags = True
        else:
            self.use_ctags = False

        self.tokenizer = main_model.tokenizer
        self.repo_content_prefix = repo_content_prefix

    def get_repo_map(self, chat_files, other_files):
        res = self.choose_files_listing(chat_files, other_files)
        if not res:
            return

        files_listing, ctags_msg = res

        if chat_files:
            other = "other "
        else:
            other = ""

        if self.repo_content_prefix:
            repo_content = self.repo_content_prefix.format(
                other=other,
                ctags_msg=ctags_msg,
            )
        else:
            repo_content = ""

        repo_content += files_listing

        return repo_content

    def choose_files_listing(self, chat_files, other_files):
        if self.max_map_tokens <= 0:
            return

        if not other_files:
            return

        if self.use_ctags:
            files_listing = self.get_ranked_tags_map(chat_files, other_files)
            if files_listing:
                num_tokens = self.token_count(files_listing)
                if self.verbose:
                    self.io.tool_output(f"ctags map: {num_tokens/1024:.1f} k-tokens")
                ctags_msg = " with selected ctags info"
                return files_listing, ctags_msg

        files_listing = self.get_simple_files_map(other_files)
        ctags_msg = ""
        num_tokens = self.token_count(files_listing)
        if self.verbose:
            self.io.tool_output(f"simple map: {num_tokens/1024:.1f} k-tokens")
        if num_tokens < self.max_map_tokens:
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

    def split_path(self, path):
        path = os.path.relpath(path, self.root)
        return [path + ":"]

    def run_ctags(self, filename):
        # Check if the file is in the cache and if the modification time has not changed
        file_mtime = self.get_mtime(filename)
        if file_mtime is None:
            return []

        cache_key = filename
        if cache_key in self.TAGS_CACHE and self.TAGS_CACHE[cache_key]["mtime"] == file_mtime:
            return self.TAGS_CACHE[cache_key]["data"]

        cmd = self.ctags_cmd + [
            f"--input-encoding={self.io.encoding}",
            filename,
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE).decode("utf-8")
        output_lines = output.splitlines()

        data = []
        for line in output_lines:
            try:
                data.append(json.loads(line))
            except json.decoder.JSONDecodeError as err:
                self.io.tool_error(f"Error parsing ctags output: {err}")
                self.io.tool_error(repr(line))

        # Update the cache
        self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
        self.save_tags_cache()
        return data

    def check_for_ctags(self):
        try:
            executable = self.ctags_cmd[0]
            cmd = [executable, "--version"]
            output = subprocess.check_output(cmd, stderr=subprocess.PIPE).decode("utf-8")
            output = output.lower()

            cmd = " ".join(cmd)

            if "universal ctags" not in output:
                self.ctags_disabled_reason = f"{cmd} does not claim to be universal ctags"
                return
            if "+json" not in output:
                self.ctags_disabled_reason = f"{cmd} does not list +json support"
                return

            with tempfile.TemporaryDirectory() as tempdir:
                hello_py = os.path.join(tempdir, "hello.py")
                with open(hello_py, "w", encoding="utf-8") as f:
                    f.write("def hello():\n    print('Hello, world!')\n")
                self.run_ctags(hello_py)
        except FileNotFoundError:
            self.ctags_disabled_reason = f"{executable} executable not found"
            return
        except Exception as err:
            self.ctags_disabled_reason = f"error running universal-ctags: {err}"
            return

        return True

    def load_tags_cache(self):
        path = Path(self.root) / self.TAGS_CACHE_DIR
        if not path.exists():
            self.cache_missing = True
        self.TAGS_CACHE = Cache(path)

    def save_tags_cache(self):
        pass

    def load_ident_cache(self):
        path = Path(self.root) / self.IDENT_CACHE_DIR
        if not path.exists():
            self.cache_missing = True
        self.IDENT_CACHE = Cache(path)

    def save_ident_cache(self):
        pass

    def get_mtime(self, fname):
        try:
            return os.path.getmtime(fname)
        except FileNotFoundError:
            self.io.tool_error(f"File not found error: {fname}")

    def get_name_identifiers(self, fname, uniq=True):
        file_mtime = self.get_mtime(fname)
        if file_mtime is None:
            return set()

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
        content = self.io.read_text(fname)
        if content is None:
            return list()

        try:
            lexer = guess_lexer_for_filename(fname, content)
        except ClassNotFound:
            return list()

        # lexer.get_tokens_unprocessed() returns (char position in file, token type, token string)
        tokens = list(lexer.get_tokens_unprocessed(content))
        res = [token[2] for token in tokens if token[1] in Token.Name]
        return res

    def get_ranked_tags(self, chat_fnames, other_fnames):
        defines = defaultdict(set)
        references = defaultdict(list)
        definitions = defaultdict(set)

        personalization = dict()

        fnames = set(chat_fnames).union(set(other_fnames))
        chat_rel_fnames = set()

        fnames = sorted(fnames)

        if self.cache_missing:
            fnames = tqdm(fnames)
        self.cache_missing = False

        for fname in fnames:
            if not Path(fname).is_file():
                self.io.tool_error(f"Repo-map can't include {fname}")
                continue

            # dump(fname)
            rel_fname = os.path.relpath(fname, self.root)

            if fname in chat_fnames:
                personalization[rel_fname] = 1.0
                chat_rel_fnames.add(rel_fname)

            data = self.run_ctags(fname)

            for tag in data:
                ident = tag["name"]
                defines[ident].add(rel_fname)

                scope = tag.get("scope")
                kind = tag.get("kind")
                name = tag.get("name")
                signature = tag.get("signature")

                last = name
                if signature:
                    last += " " + signature

                res = [rel_fname]
                if scope:
                    res.append(scope)
                res += [kind, last]

                key = (rel_fname, ident)
                definitions[key].add(tuple(res))
                # definitions[key].add((rel_fname,))

            idents = self.get_name_identifiers(fname, uniq=False)
            for ident in idents:
                # dump("ref", fname, ident)
                references[ident].append(rel_fname)

        idents = set(defines.keys()).intersection(set(references.keys()))

        G = nx.MultiDiGraph()

        for ident in idents:
            definers = defines[ident]
            for referencer, num_refs in Counter(references[ident]).items():
                for definer in definers:
                    if referencer == definer:
                        continue
                    G.add_edge(referencer, definer, weight=num_refs, ident=ident)

        if personalization:
            pers_args = dict(personalization=personalization, dangling=personalization)
        else:
            pers_args = dict()

        try:
            ranked = nx.pagerank(G, weight="weight", **pers_args)
        except ZeroDivisionError:
            return []

        # distribute the rank from each source node, across all of its out edges
        ranked_definitions = defaultdict(float)
        for src in G.nodes:
            src_rank = ranked[src]
            total_weight = sum(data["weight"] for _src, _dst, data in G.out_edges(src, data=True))
            # dump(src, src_rank, total_weight)
            for _src, dst, data in G.out_edges(src, data=True):
                data["rank"] = src_rank * data["weight"] / total_weight
                ident = data["ident"]
                ranked_definitions[(dst, ident)] += data["rank"]

        ranked_tags = []
        ranked_definitions = sorted(ranked_definitions.items(), reverse=True, key=lambda x: x[1])
        for (fname, ident), rank in ranked_definitions:
            # print(f"{rank:.03f} {fname} {ident}")
            if fname in chat_rel_fnames:
                continue
            ranked_tags += list(definitions.get((fname, ident), []))

        rel_other_fnames_without_tags = set(
            os.path.relpath(fname, self.root) for fname in other_fnames
        )

        fnames_already_included = set(rt[0] for rt in ranked_tags)

        top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
        for rank, fname in top_rank:
            if fname in rel_other_fnames_without_tags:
                rel_other_fnames_without_tags.remove(fname)
            if fname not in fnames_already_included:
                ranked_tags.append((fname,))

        for fname in rel_other_fnames_without_tags:
            ranked_tags.append((fname,))

        return ranked_tags

    def get_ranked_tags_map(self, chat_fnames, other_fnames=None):
        if not other_fnames:
            other_fnames = list()

        ranked_tags = self.get_ranked_tags(chat_fnames, other_fnames)
        num_tags = len(ranked_tags)

        lower_bound = 0
        upper_bound = num_tags
        best_tree = None

        while lower_bound <= upper_bound:
            middle = (lower_bound + upper_bound) // 2
            tree = to_tree(ranked_tags[:middle])
            num_tokens = self.token_count(tree)
            # dump(middle, num_tokens)

            if num_tokens < self.max_map_tokens:
                best_tree = tree
                lower_bound = middle + 1
            else:
                upper_bound = middle - 1

        return best_tree


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


if __name__ == "__main__":
    fnames = sys.argv[1:]

    chat_fnames = []
    other_fnames = []
    for dname in sys.argv[1:]:
        if ".venv" in dname:
            other_fnames += find_py_files(dname)
        else:
            chat_fnames += find_py_files(dname)

    root = os.path.commonpath(chat_fnames)

    rm = RepoMap(root=root)
    repo_map = rm.get_ranked_tags_map(chat_fnames, other_fnames)

    dump(len(repo_map))
    print(repo_map)
