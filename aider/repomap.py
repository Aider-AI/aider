import colorsys
import os
import random
import sys
from collections import Counter, defaultdict, namedtuple
from pathlib import Path

import networkx as nx
import pkg_resources
from diskcache import Cache
from grep_ast import TreeContext, filename_to_lang
from tqdm import tqdm
from tree_sitter_languages import get_language, get_parser

from aider import models

from .dump import dump  # noqa: F402

Tag = namedtuple("Tag", "fname rel_fname line name kind".split())


def to_tree(tags):
    if not tags:
        return ""

    tags = sorted(tags)

    cur_fname = None
    context = None
    output = ""

    # add a bogus tag at the end so we trip the this_fname != cur_fname...
    for tag in tags + [None]:
        if tag is None:
            this_fname = None
        elif type(tag) is tuple:
            this_fname = tag[0]
        else:
            this_fname = tag.rel_fname

        # ... here ... to output the final real entry in the list
        if this_fname != cur_fname:
            if context:
                context.add_context()
                if output:
                    output += "\n"
                output += cur_fname + ":\n\n"
                output += context.format()
                context = None
            elif cur_fname:
                output += cur_fname + "\n"

            if type(tag) is Tag:
                context = TreeContext(
                    tag.rel_fname,
                    Path(tag.fname).read_text(),  # TODO: encoding
                    color=False,
                    line_number=False,
                    child_context=False,
                    last_line=False,
                    margin=0,
                    mark_lois=False,
                    loi_pad=0,
                    header_max=3,
                )
            cur_fname = this_fname

        if context:
            context.add_lines_of_interest([tag.line])

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
    CACHE_VERSION = 2
    TAGS_CACHE_DIR = f".aider.tags.cache.v{CACHE_VERSION}"

    cache_missing = False

    warned_files = set()

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

        self.load_tags_cache()

        self.max_map_tokens = map_tokens

        self.tokenizer = main_model.tokenizer
        self.repo_content_prefix = repo_content_prefix

    def get_repo_map(self, chat_files, other_files):
        if self.max_map_tokens <= 0:
            return

        if not other_files:
            return

        files_listing = self.get_ranked_tags_map(chat_files, other_files)
        if not files_listing:
            return

        num_tokens = self.token_count(files_listing)
        if self.verbose:
            self.io.tool_output(f"ast map: {num_tokens/1024:.1f} k-tokens")

        if chat_files:
            other = "other "
        else:
            other = ""

        if self.repo_content_prefix:
            repo_content = self.repo_content_prefix.format(other=other)
        else:
            repo_content = ""

        repo_content += files_listing

        return repo_content

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

    def load_tags_cache(self):
        path = Path(self.root) / self.TAGS_CACHE_DIR
        if not path.exists():
            self.cache_missing = True
        self.TAGS_CACHE = Cache(path)

    def save_tags_cache(self):
        pass

    def get_mtime(self, fname):
        try:
            return os.path.getmtime(fname)
        except FileNotFoundError:
            self.io.tool_error(f"File not found error: {fname}")

    def get_tags(self, fname, rel_fname):
        lang = filename_to_lang(fname)
        if not lang:
            return

        language = get_language(lang)
        parser = get_parser(lang)

        # Load the tags queries
        scm_fname = pkg_resources.resource_filename(
            __name__, os.path.join("queries", f"tree-sitter-{lang}-tags.scm")
        )
        query_scm = Path(scm_fname)
        if not query_scm.exists():
            return
        query_scm = query_scm.read_text()

        code = Path(fname).read_text()  # TODO: encoding
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the tags queries
        query = language.query(query_scm)
        captures = query.captures(tree.root_node)

        captures = list(captures)

        for node, tag in captures:
            if tag.startswith("name.definition."):
                kind = "def"
            elif tag.startswith("name.reference."):
                kind = "ref"
            else:
                continue

            result = Tag(
                fname=fname,
                rel_fname=rel_fname,
                name=node.text.decode("utf-8"),
                kind=kind,
                line=node.start_point[0],
            )

            yield result

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
                if fname not in self.warned_files:
                    self.io.tool_error(f"Repo-map can't include {fname}")

                self.warned_files.add(fname)
                continue

            # dump(fname)
            rel_fname = os.path.relpath(fname, self.root)

            if fname in chat_fnames:
                personalization[rel_fname] = 1.0
                chat_rel_fnames.add(rel_fname)

            tags = self.get_tags(fname, rel_fname)
            if tags is None:
                continue

            for tag in tags:
                if tag.kind == "def":
                    defines[tag.name].add(rel_fname)
                    key = (rel_fname, tag.name)
                    definitions[key].add(tag)

                if tag.kind == "ref":
                    references[tag.name].append(rel_fname)

        ##
        # dump(definitions)
        # dump(references)

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


def find_src_files(directory):
    if not os.path.isdir(directory):
        return [directory]

    src_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            src_files.append(os.path.join(root, file))
    return src_files


def get_random_color():
    hue = random.random()
    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 0.75)]
    res = f"#{r:02x}{g:02x}{b:02x}"
    return res


if __name__ == "__main__":
    fnames = sys.argv[1:]

    chat_fnames = []
    other_fnames = []
    for fname in sys.argv[1:]:
        if Path(fname).is_dir():
            chat_fnames += find_src_files(fname)
        else:
            chat_fnames.append(fname)

    rm = RepoMap(root=".")
    repo_map = rm.get_ranked_tags_map(chat_fnames, other_fnames)

    dump(len(repo_map))
    print(repo_map)
