"""Python bindings for tree-sitter."""

from ctypes import c_void_p, cdll
from enum import IntEnum
from os import PathLike, fspath, path
from platform import system
from tempfile import TemporaryDirectory
from typing import List, Optional, Union
from warnings import warn

from tree_sitter._binding import (
    LookaheadIterator,
    LookaheadNamesIterator,
    Node,
    Parser,
    Query,
    Range,
    Tree,
    TreeCursor,
    _language_field_count,
    _language_field_id_for_name,
    _language_field_name_for_id,
    _language_query,
    _language_state_count,
    _language_symbol_count,
    _language_symbol_for_name,
    _language_symbol_name,
    _language_symbol_type,
    _language_version,
    _lookahead_iterator,
    _next_state,
)


def _deprecate(old: str, new: str):
    warn("{} is deprecated. Use {} instead.".format(old, new), FutureWarning)


class SymbolType(IntEnum):
    """An enumeration of the different types of symbols."""

    REGULAR = 0
    """A regular symbol."""

    ANONYMOUS = 1
    """An anonymous symbol."""

    AUXILIARY = 2
    """An auxiliary symbol."""


class Language:
    """A tree-sitter language"""

    @staticmethod
    def build_library(output_path: str, repo_paths: List[str]) -> bool:
        """
        Build a dynamic library at the given path, based on the parser
        repositories at the given paths.

        Returns `True` if the dynamic library was compiled and `False` if
        the library already existed and was modified more recently than
        any of the source files.
        """
        _deprecate("Language.build_library", "the new bindings")
        output_mtime = path.getmtime(output_path) if path.exists(output_path) else 0

        if not repo_paths:
            raise ValueError("Must provide at least one language folder")

        cpp = False
        source_paths = []
        for repo_path in repo_paths:
            src_path = path.join(repo_path, "src")
            source_paths.append(path.join(src_path, "parser.c"))
            if path.exists(path.join(src_path, "scanner.cc")):
                cpp = True
                source_paths.append(path.join(src_path, "scanner.cc"))
            elif path.exists(path.join(src_path, "scanner.c")):
                source_paths.append(path.join(src_path, "scanner.c"))
        source_mtimes = [path.getmtime(__file__)] + [path.getmtime(path_) for path_ in source_paths]

        if max(source_mtimes) <= output_mtime:
            return False

        # local import saves import time in the common case that nothing is compiled
        try:
            from distutils.ccompiler import new_compiler
            from distutils.unixccompiler import UnixCCompiler
        except ImportError as err:
            raise RuntimeError(
                "Failed to import distutils. You may need to install setuptools."
            ) from err

        compiler = new_compiler()
        if isinstance(compiler, UnixCCompiler):
            compiler.set_executables(compiler_cxx="c++")

        with TemporaryDirectory(suffix="tree_sitter_language") as out_dir:
            object_paths = []
            for source_path in source_paths:
                if system() == "Windows":
                    flags = None
                else:
                    flags = ["-fPIC"]
                    if source_path.endswith(".c"):
                        flags.append("-std=c11")
                object_paths.append(
                    compiler.compile(
                        [source_path],
                        output_dir=out_dir,
                        include_dirs=[path.dirname(source_path)],
                        extra_preargs=flags,
                    )[0]
                )
            compiler.link_shared_object(
                object_paths,
                output_path,
                target_lang="c++" if cpp else "c",
            )
        return True

    def __init__(self, path_or_ptr: Union[PathLike, str, int], name: str):
        """
        Load the language with the given language pointer from the dynamic library,
        or load the language with the given name from the dynamic library at the
        given path.
        """
        if isinstance(path_or_ptr, (str, PathLike)):
            _deprecate("Language(path, name)", "Language(ptr, name)")
            self.name = name
            self.lib = cdll.LoadLibrary(fspath(path_or_ptr))
            language_function = getattr(self.lib, "tree_sitter_%s" % name)
            language_function.restype = c_void_p
            self.language_id = language_function()
        elif isinstance(path_or_ptr, int):
            self.name = name
            self.language_id = path_or_ptr
        else:
            raise TypeError("Expected a path or pointer for the first argument")

    @property
    def version(self) -> int:
        """
        Get the ABI version number that indicates which version of the Tree-sitter CLI
        that was used to generate this [`Language`].
        """
        return _language_version(self.language_id)

    @property
    def node_kind_count(self) -> int:
        """Get the number of distinct node types in this language."""
        return _language_symbol_count(self.language_id)

    @property
    def parse_state_count(self) -> int:
        """Get the number of valid states in this language."""
        return _language_state_count(self.language_id)

    def node_kind_for_id(self, id: int) -> Optional[str]:
        """Get the name of the node kind for the given numerical id."""
        return _language_symbol_name(self.language_id, id)

    def id_for_node_kind(self, kind: str, named: bool) -> Optional[int]:
        """Get the numerical id for the given node kind."""
        return _language_symbol_for_name(self.language_id, kind, named)

    def node_kind_is_named(self, id: int) -> bool:
        """
        Check if the node type for the given numerical id is named
        (as opposed to an anonymous node type).
        """
        return _language_symbol_type(self.language_id, id) == SymbolType.REGULAR

    def node_kind_is_visible(self, id: int) -> bool:
        """
        Check if the node type for the given numerical id is visible
        (as opposed to an auxiliary node type).
        """
        return _language_symbol_type(self.language_id, id) <= SymbolType.ANONYMOUS

    @property
    def field_count(self) -> int:
        """Get the number of fields in this language."""
        return _language_field_count(self.language_id)

    def field_name_for_id(self, field_id: int) -> Optional[str]:
        """Get the name of the field for the given numerical id."""
        return _language_field_name_for_id(self.language_id, field_id)

    def field_id_for_name(self, name: str) -> Optional[int]:
        """Return the field id for a field name."""
        return _language_field_id_for_name(self.language_id, name)

    def next_state(self, state: int, id: int) -> int:
        """
        Get the next parse state. Combine this with `lookahead_iterator` to
        generate completion suggestions or valid symbols in error nodes.
        """
        return _next_state(self.language_id, state, id)

    def lookahead_iterator(self, state: int) -> Optional[LookaheadIterator]:
        """
        Create a new lookahead iterator for this language and parse state.

        This returns `None` if state is invalid for this language.

        Iterating `LookaheadIterator` will yield valid symbols in the given
        parse state. Newly created lookahead iterators will return the `ERROR`
        symbol from `LookaheadIterator.current_symbol`.

        Lookahead iterators can be useful to generate suggestions and improve
        syntax error diagnostics. To get symbols valid in an ERROR node, use the
        lookahead iterator on its first leaf node state. For `MISSING` nodes, a
        lookahead iterator created on the previous non-extra leaf node may be
        appropriate.
        """
        return _lookahead_iterator(self.language_id, state)

    def query(self, source: str) -> Query:
        """Create a Query with the given source code."""
        return _language_query(self.language_id, source)


__all__ = [
    "Language",
    "Node",
    "Parser",
    "Query",
    "Range",
    "Tree",
    "TreeCursor",
    "LookaheadIterator",
    "LookaheadNamesIterator",
]
