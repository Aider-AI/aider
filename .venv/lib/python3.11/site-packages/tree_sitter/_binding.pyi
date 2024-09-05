from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import tree_sitter

class Node:
    """A syntax node"""

    def sexp(self) -> str:
        """Get an S-expression representing the node."""

    def walk(self) -> TreeCursor:
        """Get a tree cursor for walking the tree starting at this node."""

    def edit(
        self,
        start_byte: int,
        old_end_byte: int,
        new_end_byte: int,
        start_point: Tuple[int, int],
        old_end_point: Tuple[int, int],
        new_end_point: Tuple[int, int],
    ) -> None:
        """Edit this node to keep it in-sync with source code that has been edited."""

    def child(self, index: int) -> Optional[Node]:
        """Get child at the given index."""

    def named_child(self, index: int) -> Optional[Node]:
        """Get named child at the given index."""

    def child_by_field_id(self, id: int) -> Optional[Node]:
        """Get child for the given field id."""

    def child_by_field_name(self, name: str) -> Optional[Node]:
        """Get child for the given field name."""

    def children_by_field_id(self, id: int) -> List[Node]:
        """Get a list of child nodes for the given field id."""

    def children_by_field_name(self, name: str) -> List[Node]:
        """Get a list of child nodes for the given field name."""

    def field_name_for_child(self, child_index: int) -> Optional[str]:
        """Get the field name of a child node by the index of child."""

    def descendant_for_byte_range(self, start_byte: int, end_byte: int) -> Optional[Node]:
        """Get the smallest node within the given byte range."""

    def named_descendant_for_byte_range(self, start_byte: int, end_byte: int) -> Optional[Node]:
        """Get the smallest named node within the given byte range."""

    def descendant_for_point_range(
        self, start_point: Tuple[int, int], end_point: Tuple[int, int]
    ) -> Optional[Node]:
        """Get the smallest node within this node that spans the given point range."""

    def named_descendant_for_point_range(
        self, start_point: Tuple[int, int], end_point: Tuple[int, int]
    ) -> Optional[Node]:
        """Get the smallest named node within this node that spans the given point range."""

    @property
    def id(self) -> int:
        """The node's numeric id"""

    @property
    def kind_id(self) -> int:
        """The node's type as a numerical id"""

    @property
    def grammar_id(self) -> int:
        """The node's grammar type as a numerical id"""

    @property
    def grammar_name(self) -> str:
        """The node's grammar name as a string"""

    @property
    def type(self) -> str:
        """The node's type"""

    @property
    def is_named(self) -> bool:
        """Is this a named node"""

    @property
    def is_extra(self) -> bool:
        """Is this an extra node"""

    @property
    def has_changes(self) -> bool:
        """Does this node have text changes since it was parsed"""

    @property
    def has_error(self) -> bool:
        """Does this node contain any errors"""

    @property
    def is_error(self) -> bool:
        """Is this node an error"""

    @property
    def parse_state(self) -> int:
        """The node's parse state"""

    @property
    def next_parse_state(self) -> int:
        """The parse state after this node's"""

    @property
    def is_missing(self) -> bool:
        """Is this a node inserted by the parser"""

    @property
    def start_byte(self) -> int:
        """The node's start byte"""

    @property
    def end_byte(self) -> int:
        """The node's end byte"""

    @property
    def byte_range(self) -> Tuple[int, int]:
        """The node's byte range"""

    @property
    def range(self) -> Range:
        """The node's range"""

    @property
    def start_point(self) -> Tuple[int, int]:
        """The node's start point"""

    @property
    def end_point(self) -> Tuple[int, int]:
        """The node's end point"""

    @property
    def children(self) -> List[Node]:
        """The node's children"""

    @property
    def child_count(self) -> int:
        """The number of children for a node"""

    @property
    def named_children(self) -> List[Node]:
        """The node's named children"""

    @property
    def named_child_count(self) -> int:
        """The number of named children for a node"""

    @property
    def parent(self) -> Optional[Node]:
        """The node's parent"""

    @property
    def next_sibling(self) -> Optional[Node]:
        """The node's next sibling"""

    @property
    def prev_sibling(self) -> Optional[Node]:
        """The node's previous sibling"""

    @property
    def next_named_sibling(self) -> Optional[Node]:
        """The node's next named sibling"""

    @property
    def prev_named_sibling(self) -> Optional[Node]:
        """The node's previous named sibling"""

    @property
    def descendant_count(self) -> int:
        """The number of descendants for a node, including itself"""

    @property
    def text(self) -> bytes:
        """The node's text, if tree has not been edited"""

class Tree:
    """A Syntax Tree"""

    def root_node_with_offset(
        self, offset_bytes: int, offset_extent: Tuple[int, int]
    ) -> Optional[Node]:
        """Get the root node of the syntax tree, but with its position shifted forward by the given offset."""

    def walk(self) -> TreeCursor:
        """Get a tree cursor for walking this tree."""

    def edit(
        self,
        start_byte: int,
        old_end_byte: int,
        new_end_byte: int,
        start_point: Tuple[int, int],
        old_end_point: Tuple[int, int],
        new_end_point: Tuple[int, int],
    ) -> None:
        """Edit the syntax tree."""

    def changed_ranges(self, old_tree: Tree) -> List[Range]:
        """Get a list of ranges that were edited."""

    @property
    def included_ranges(self) -> List[Range]:
        """Get the included ranges that were used to parse the syntax tree."""

    @property
    def root_node(self) -> Node:
        """The root node of this tree."""

    @property
    def text(self) -> bytes:
        """The source text for this tree, if unedited."""

class TreeCursor:
    """A syntax tree cursor."""

    def descendant_index(self) -> int:
        """Get the index of the cursor's current node out of all of the descendants of the original node."""

    def goto_first_child(self) -> bool:
        """Go to the first child.
        If the current node has children, move to the first child and
        return True. Otherwise, return False.
        """

    def goto_last_child(self) -> bool:
        """Go to the last child.
        If the current node has children, move to the last child and
        return True. Otherwise, return False.
        """

    def goto_parent(self) -> bool:
        """Go to the parent.
        If the current node is not the root, move to its parent and
        return True. Otherwise, return False.
        """

    def goto_next_sibling(self) -> bool:
        """Go to the next sibling.

        If the current node has a next sibling, move to the next sibling
        and return True. Otherwise, return False.
        """

    def goto_previous_sibling(self) -> bool:
        """Go to the previous sibling.

        If the current node has a previous sibling, move to the previous sibling
        and return True. Otherwise, return False.
        """

    def goto_descendant(self, index: int) -> None:
        """Go to the descendant at the given index.

        If the current node has a descendant at the given index, move to the
        descendant and return True. Otherwise, return False.
        """

    def goto_first_child_for_byte(self, byte: int) -> bool:
        """Go to the first child that extends beyond the given byte.

        If the current node has a child that includes the given byte, move to the
        child and return True. Otherwise, return False.
        """

    def goto_first_child_for_point(self, row: int, column: int) -> bool:
        """Go to the first child that extends beyond the given point.

        If the current node has a child that includes the given point, move to the
        child and return True. Otherwise, return False.
        """

    def reset(self, node: Node) -> None:
        """Re-initialize a tree cursor to start at a different node."""

    def reset_to(self, cursor: TreeCursor) -> None:
        """Re-initialize the cursor to the same position as the given cursor.

        Unlike `reset`, this will not lose parent information and allows reusing already created cursors
        """

    def copy(self) -> TreeCursor:
        """Create a copy of the cursor."""

    @property
    def node(self) -> Node:
        """The current node."""

    @property
    def field_id(self) -> Optional[int]:
        """Get the field id of the tree cursor's current node.

        If the current node has the field id, return int. Otherwise, return None.
        """

    @property
    def field_name(self) -> Optional[str]:
        """Get the field name of the tree cursor's current node.

        If the current node has the field name, return str. Otherwise, return None.
        """

    @property
    def depth(self) -> int:
        """Get the depth of the cursor's current node relative to the original node."""

class Parser:
    """A Parser"""

    def parse(
        self,
        source_code: bytes | Callable[[int, Tuple[int, int]], Optional[bytes]],
        old_tree: Optional[Tree] = None,
        keep_text: Optional[bool] = True,
    ) -> Tree:
        """Parse source code, creating a syntax tree.
        Note that by default `keep_text` will be True, unless source_code is a callable.
        """

    def reset(self) -> None:
        """Instruct the parser to start the next parse from the beginning."""

    def set_timeout_micros(self, timeout: int) -> None:
        """Set the maximum duration in microseconds that parsing should be allowed to take before halting."""

    def set_included_ranges(self, ranges: List[Range]) -> None:
        """Set the ranges of text that the parser should include when parsing."""

    def set_language(self, language: tree_sitter.Language) -> None:
        """Set the parser language."""

    @property
    def timeout_micros(self) -> int:
        """The timeout for parsing, in microseconds."""

class Query:
    """A set of patterns to search for in a syntax tree."""

    def matches(
        self,
        node: Node,
        start_point: Optional[Tuple[int, int]] = None,
        end_point: Optional[Tuple[int, int]] = None,
        start_byte: Optional[int] = None,
        end_byte: Optional[int] = None,
    ) -> List[Tuple[int, Dict[str, Union[Node, List[Node]]]]]:
        """Get a list of all of the matches within the given node."""

    def captures(
        self,
        node: Node,
        start_point: Optional[Tuple[int, int]] = None,
        end_point: Optional[Tuple[int, int]] = None,
        start_byte: Optional[int] = None,
        end_byte: Optional[int] = None,
    ) -> List[Tuple[Node, str]]:
        """Get a list of all of the captures within the given node."""

class LookaheadIterator(Iterable):
    def reset(self, language: int, state: int) -> None:
        """Reset the lookahead iterator to a new language and parse state.

        This returns `True` if the language was set successfully, and `False` otherwise.
        """

    def reset_state(self, state: int) -> None:
        """Reset the lookahead iterator to another state.

        This returns `True` if the iterator was reset to the given state, and `False` otherwise.
        """

    @property
    def language(self) -> int:
        """Get the language."""

    @property
    def current_symbol(self) -> int:
        """Get the current symbol."""

    @property
    def current_symbol_name(self) -> str:
        """Get the current symbol name."""

    def __next__(self) -> int:
        """Get the next symbol."""

    def __iter__(self) -> LookaheadIterator:
        """Get an iterator for the lookahead iterator."""

    def iter_names(self) -> LookaheadNamesIterator:
        """Get an iterator for the lookahead iterator."""

class LookaheadNamesIterator(Iterable):
    def __next__(self) -> str:
        """Get the next symbol name."""

    def __iter__(self) -> LookaheadNamesIterator:
        """Get an iterator for the lookahead names iterator."""

@dataclass
class Range:
    """A range within a document."""

    start_point: Tuple[int, int]
    """The start point of this range"""

    end_point: Tuple[int, int]
    """The end point of this range"""

    start_byte: int
    """The start byte of this range"""

    end_byte: int
    """The end byte of this range"""

    def __init__(
        self,
        start_point: Tuple[int, int],
        end_point: Tuple[int, int],
        start_byte: int,
        end_byte: int,
    ) -> None:
        """Create a new range."""

    def __repr__(self) -> str:
        """Get a string representation of the range."""

    def __eq__(self, other: Any) -> bool:
        """Check if two ranges are equal."""

    def __ne__(self, other: Any) -> bool:
        """Check if two ranges are not equal."""

def _language_version(language_id: int) -> int:
    ...

def _language_symbol_count(language_id: int) -> int:
    ...

def _language_state_count(language_id: int) -> int:
    ...

def _language_symbol_name(language_id: int, id: int) -> Optional[str]:
    ...

def _language_symbol_for_name(language_id: int, name: str, named: bool) -> Optional[int]:
    ...

def _language_symbol_type(language_id: int, id: int) -> int:
    ...

def _language_field_count(language_id: int) -> int:
    ...

def _language_field_name_for_id(language_id: int, field_id: int) -> Optional[str]:
    ...

def _language_field_id_for_name(language_id: int, name: str) -> Optional[int]:
    ...

def _language_query(language_id: int, source: str) -> Query:
    ...

def _lookahead_iterator(language_id: int, state: int) -> Optional[LookaheadIterator]:
    ...

def _next_state(language_id: int, state: int, symbol: int) -> int:
    ...
