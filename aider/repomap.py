import colorsys
import math
import os
import random
import sys
import warnings
from collections import Counter, defaultdict, namedtuple
from importlib import resources
from pathlib import Path

from diskcache import Cache
from grep_ast import TreeContext, filename_to_lang
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound
from tqdm import tqdm

from aider.dump import dump
from aider.utils import Spinner

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_language, get_parser  # noqa: E402

Tag = namedtuple("Tag", "rel_fname fname line name kind".split())


class RepoMap:
    CACHE_VERSION = 3
    TAGS_CACHE_DIR = f".aider.tags.cache.v{CACHE_VERSION}"

    warned_files = set()

    def __init__(
        self,
        map_tokens=1024,
        root=None,
        main_model=None,
        io=None,
        repo_content_prefix=None,
        verbose=False,
        max_context_window=None,
        map_mul_no_files=8,
    ):
        self.io = io
        self.verbose = verbose

        if not root:
            root = os.getcwd()
        self.root = root

        self.load_tags_cache()
        self.cache_threshold = 0.95

        self.max_map_tokens = map_tokens
        self.map_mul_no_files = map_mul_no_files
        self.max_context_window = max_context_window

        self.repo_content_prefix = repo_content_prefix

        self.main_model = main_model

        self.tree_cache = {}
        self.tree_context_cache = {}

    def token_count(self, text):
        len_text = len(text)
        if len_text < 200:
            return self.main_model.token_count(text)

        lines = text.splitlines(keepends=True)
        num_lines = len(lines)
        step = num_lines // 100 or 1
        lines = lines[::step]
        sample_text = "".join(lines)
        sample_tokens = self.main_model.token_count(sample_text)
        est_tokens = sample_tokens / len(sample_text) * len_text
        return est_tokens

    def get_repo_map(self, chat_files, other_files, mentioned_fnames=None, mentioned_idents=None):
        if self.max_map_tokens <= 0:
            return
        if not other_files:
            return
        if not mentioned_fnames:
            mentioned_fnames = set()
        if not mentioned_idents:
            mentioned_idents = set()

        max_map_tokens = self.max_map_tokens

        # With no files in the chat, give a bigger view of the entire repo
        padding = 4096
        if max_map_tokens and self.max_context_window:
            target = min(
                max_map_tokens * self.map_mul_no_files,
                self.max_context_window - padding,
            )
        else:
            target = 0
        if not chat_files and self.max_context_window and target > 0:
            max_map_tokens = target

        try:
            files_listing = self.get_ranked_tags_map(
                chat_files, other_files, max_map_tokens, mentioned_fnames, mentioned_idents
            )
        except RecursionError:
            self.io.tool_error("Disabling repo map, git repo too large?")
            self.max_map_tokens = 0
            return

        if not files_listing:
            return

        if self.verbose:
            num_tokens = self.token_count(files_listing)
            self.io.tool_output(f"Repo-map: {num_tokens / 1024:.1f} k-tokens")

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
        # Check if the file is in the cache and if the modification time has not changed
        file_mtime = self.get_mtime(fname)
        if file_mtime is None:
            return []

        cache_key = fname
        if cache_key in self.TAGS_CACHE and self.TAGS_CACHE[cache_key]["mtime"] == file_mtime:
            return self.TAGS_CACHE[cache_key]["data"]

        # miss!
        data = list(self.get_tags_raw(fname, rel_fname))

        # Update the cache
        self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
        self.save_tags_cache()
        return data

    def get_tags_raw(self, fname, rel_fname):
        lang = filename_to_lang(fname)
        if not lang:
            return

        language = get_language(lang)
        parser = get_parser(lang)

        query_scm = get_scm_fname(lang)
        if not query_scm.exists():
            return
        query_scm = query_scm.read_text()

        code = self.io.read_text(fname)
        if not code:
            return
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the tags queries
        query = language.query(query_scm)
        captures = query.captures(tree.root_node)

        captures = list(captures)

        saw = set()
        for node, tag in captures:
            if tag.startswith("name.definition."):
                kind = "def"
            elif tag.startswith("name.reference."):
                kind = "ref"
            else:
                continue

            saw.add(kind)

            result = Tag(
                rel_fname=rel_fname,
                fname=fname,
                name=node.text.decode("utf-8"),
                kind=kind,
                line=node.start_point[0],
            )

            yield result

        if "ref" in saw:
            return
        if "def" not in saw:
            return

        # We saw defs, without any refs
        # Some tags files only provide defs (cpp, for example)
        # Use pygments to backfill refs

        try:
            lexer = guess_lexer_for_filename(fname, code)
        except ClassNotFound:
            return

        tokens = list(lexer.get_tokens(code))
        tokens = [token[1] for token in tokens if token[0] in Token.Name]

        for token in tokens:
            yield Tag(
                rel_fname=rel_fname,
                fname=fname,
                name=token,
                kind="ref",
                line=-1,
            )

    def get_ranked_tags(
        self, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents, progress=None
    ):
        import networkx as nx

        defines = defaultdict(set)
        references = defaultdict(list)
        definitions = defaultdict(set)

        personalization = dict()

        fnames = set(chat_fnames).union(set(other_fnames))
        chat_rel_fnames = set()

        fnames = sorted(fnames)

        # Default personalization for unspecified files is 1/num_nodes
        # https://networkx.org/documentation/stable/_modules/networkx/algorithms/link_analysis/pagerank_alg.html#pagerank
        personalize = 100 / len(fnames)

        if len(fnames) - len(self.TAGS_CACHE) > 100:
            self.io.tool_output(
                "Initial repo scan can be slow in larger repos, but only happens once."
            )
            fnames = tqdm(fnames, desc="Scanning repo")
            showing_bar = True
        else:
            showing_bar = False

        for fname in fnames:
            if progress and not showing_bar:
                progress()

            if not Path(fname).is_file():
                if fname not in self.warned_files:
                    if Path(fname).exists():
                        self.io.tool_error(
                            f"Repo-map can't include {fname}, it is not a normal file"
                        )
                    else:
                        self.io.tool_error(f"Repo-map can't include {fname}, it no longer exists")

                self.warned_files.add(fname)
                continue

            # dump(fname)
            rel_fname = self.get_rel_fname(fname)

            if fname in chat_fnames:
                personalization[rel_fname] = personalize
                chat_rel_fnames.add(rel_fname)

            if rel_fname in mentioned_fnames:
                personalization[rel_fname] = personalize

            tags = list(self.get_tags(fname, rel_fname))
            if tags is None:
                continue

            for tag in tags:
                if tag.kind == "def":
                    defines[tag.name].add(rel_fname)
                    key = (rel_fname, tag.name)
                    definitions[key].add(tag)

                elif tag.kind == "ref":
                    references[tag.name].append(rel_fname)

        ##
        # dump(defines)
        # dump(references)
        # dump(personalization)

        if not references:
            references = dict((k, list(v)) for k, v in defines.items())

        idents = set(defines.keys()).intersection(set(references.keys()))

        G = nx.MultiDiGraph()

        for ident in idents:
            if progress:
                progress()

            definers = defines[ident]
            if ident in mentioned_idents:
                mul = 10
            elif ident.startswith("_"):
                mul = 0.1
            else:
                mul = 1

            for referencer, num_refs in Counter(references[ident]).items():
                for definer in definers:
                    # dump(referencer, definer, num_refs, mul)
                    # if referencer == definer:
                    #    continue

                    # scale down so high freq (low value) mentions don't dominate
                    num_refs = math.sqrt(num_refs)

                    G.add_edge(referencer, definer, weight=mul * num_refs, ident=ident)

        if not references:
            pass

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
            if progress:
                progress()

            src_rank = ranked[src]
            total_weight = sum(data["weight"] for _src, _dst, data in G.out_edges(src, data=True))
            # dump(src, src_rank, total_weight)
            for _src, dst, data in G.out_edges(src, data=True):
                data["rank"] = src_rank * data["weight"] / total_weight
                ident = data["ident"]
                ranked_definitions[(dst, ident)] += data["rank"]

        ranked_tags = []
        ranked_definitions = sorted(ranked_definitions.items(), reverse=True, key=lambda x: x[1])

        # dump(ranked_definitions)

        for (fname, ident), rank in ranked_definitions:
            # print(f"{rank:.03f} {fname} {ident}")
            if fname in chat_rel_fnames:
                continue
            ranked_tags += list(definitions.get((fname, ident), []))

        rel_other_fnames_without_tags = set(self.get_rel_fname(fname) for fname in other_fnames)

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

    def get_ranked_tags_map(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
    ):
        if not other_fnames:
            other_fnames = list()
        if not max_map_tokens:
            max_map_tokens = self.max_map_tokens
        if not mentioned_fnames:
            mentioned_fnames = set()
        if not mentioned_idents:
            mentioned_idents = set()

        spin = Spinner("Preparing repo map")

        ranked_tags = self.get_ranked_tags(
            chat_fnames,
            other_fnames,
            mentioned_fnames,
            mentioned_idents,
            progress=spin.step,
        )

        spin.step()

        num_tags = len(ranked_tags)
        lower_bound = 0
        upper_bound = num_tags
        best_tree = None
        best_tree_tokens = 0

        chat_rel_fnames = set(self.get_rel_fname(fname) for fname in chat_fnames)

        self.tree_cache = dict()

        middle = min(max_map_tokens // 25, num_tags)
        while lower_bound <= upper_bound:
            # dump(lower_bound, middle, upper_bound)

            spin.step()

            tree = self.to_tree(ranked_tags[:middle], chat_rel_fnames)
            num_tokens = self.token_count(tree)

            pct_err = abs(num_tokens - max_map_tokens) / max_map_tokens
            ok_err = 0.15
            if (num_tokens <= max_map_tokens and num_tokens > best_tree_tokens) or pct_err < ok_err:
                best_tree = tree
                best_tree_tokens = num_tokens

                if pct_err < ok_err:
                    break

            if num_tokens < max_map_tokens:
                lower_bound = middle + 1
            else:
                upper_bound = middle - 1

            middle = (lower_bound + upper_bound) // 2

        spin.end()
        return best_tree

    tree_cache = dict()

    def render_tree(self, abs_fname, rel_fname, lois):
        key = (rel_fname, tuple(sorted(lois)))

        if key in self.tree_cache:
            return self.tree_cache[key]

        if rel_fname not in self.tree_context_cache:
            code = self.io.read_text(abs_fname) or ""
            if not code.endswith("\n"):
                code += "\n"

            context = TreeContext(
                rel_fname,
                code,
                color=False,
                line_number=False,
                child_context=False,
                last_line=False,
                margin=0,
                mark_lois=False,
                loi_pad=0,
                # header_max=30,
                show_top_of_file_parent_scope=False,
            )
            self.tree_context_cache[rel_fname] = context

        context = self.tree_context_cache[rel_fname]
        context.lines_of_interest = set()
        context.add_lines_of_interest(lois)
        context.add_context()
        res = context.format()
        self.tree_cache[key] = res
        return res

    def to_tree(self, tags, chat_rel_fnames):
        if not tags:
            return ""

        cur_fname = None
        cur_abs_fname = None
        lois = None
        output = ""

        # add a bogus tag at the end so we trip the this_fname != cur_fname...
        dummy_tag = (None,)
        for tag in sorted(tags) + [dummy_tag]:
            this_rel_fname = tag[0]
            if this_rel_fname in chat_rel_fnames:
                continue

            # ... here ... to output the final real entry in the list
            if this_rel_fname != cur_fname:
                if lois is not None:
                    output += "\n"
                    output += cur_fname + ":\n"
                    output += self.render_tree(cur_abs_fname, cur_fname, lois)
                    lois = None
                elif cur_fname:
                    output += "\n" + cur_fname + "\n"
                if type(tag) is Tag:
                    lois = []
                    cur_abs_fname = tag.fname
                cur_fname = this_rel_fname

            if lois is not None:
                lois.append(tag.line)

        # truncate long lines, in case we get minified js or something else crazy
        output = "\n".join([line[:100] for line in output.splitlines()]) + "\n"

        return output


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


def get_scm_fname(lang):
    # Load the tags queries
    try:
        return resources.files(__package__).joinpath("queries", f"tree-sitter-{lang}-tags.scm")
    except KeyError:
        return


def get_supported_languages_md():
    from grep_ast.parsers import PARSERS

    res = """
| Language | File extension | Repo map | Linter |
|:--------:|:--------------:|:--------:|:------:|
"""
    data = sorted((lang, ex) for ex, lang in PARSERS.items())

    for lang, ext in data:
        fn = get_scm_fname(lang)
        repo_map = "✓" if Path(fn).exists() else ""
        linter_support = "✓"
        res += f"| {lang:20} | {ext:20} | {repo_map:^8} | {linter_support:^6} |\n"

    res += "\n"

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
