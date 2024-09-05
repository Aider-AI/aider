"""Unit tests for pydot drawing functions."""
import os
import tempfile
from io import StringIO

import pytest

import networkx as nx
from networkx.utils import graphs_equal

pydot = pytest.importorskip("pydot")


@pytest.mark.xfail
class TestPydot:
    def pydot_checks(self, G, prog):
        """
        Validate :mod:`pydot`-based usage of the passed NetworkX graph with the
        passed basename of an external GraphViz command (e.g., `dot`, `neato`).
        """

        # Set the name of this graph to... "G". Failing to do so will
        # subsequently trip an assertion expecting this name.
        G.graph["name"] = "G"

        # Add arbitrary nodes and edges to the passed empty graph.
        G.add_edges_from([("A", "B"), ("A", "C"), ("B", "C"), ("A", "D")])
        G.add_node("E")

        # Validate layout of this graph with the passed GraphViz command.
        graph_layout = nx.nx_pydot.pydot_layout(G, prog=prog)
        assert isinstance(graph_layout, dict)

        # Convert this graph into a "pydot.Dot" instance.
        P = nx.nx_pydot.to_pydot(G)

        # Convert this "pydot.Dot" instance back into a graph of the same type.
        G2 = G.__class__(nx.nx_pydot.from_pydot(P))

        # Validate the original and resulting graphs to be the same.
        assert graphs_equal(G, G2)

        fd, fname = tempfile.mkstemp()

        # Serialize this "pydot.Dot" instance to a temporary file in dot format
        P.write_raw(fname)

        # Deserialize a list of new "pydot.Dot" instances back from this file.
        Pin_list = pydot.graph_from_dot_file(path=fname, encoding="utf-8")

        # Validate this file to contain only one graph.
        assert len(Pin_list) == 1

        # The single "pydot.Dot" instance deserialized from this file.
        Pin = Pin_list[0]

        # Sorted list of all nodes in the original "pydot.Dot" instance.
        n1 = sorted(p.get_name() for p in P.get_node_list())

        # Sorted list of all nodes in the deserialized "pydot.Dot" instance.
        n2 = sorted(p.get_name() for p in Pin.get_node_list())

        # Validate these instances to contain the same nodes.
        assert n1 == n2

        # Sorted list of all edges in the original "pydot.Dot" instance.
        e1 = sorted((e.get_source(), e.get_destination()) for e in P.get_edge_list())

        # Sorted list of all edges in the original "pydot.Dot" instance.
        e2 = sorted((e.get_source(), e.get_destination()) for e in Pin.get_edge_list())

        # Validate these instances to contain the same edges.
        assert e1 == e2

        # Deserialize a new graph of the same type back from this file.
        Hin = nx.nx_pydot.read_dot(fname)
        Hin = G.__class__(Hin)

        # Validate the original and resulting graphs to be the same.
        assert graphs_equal(G, Hin)

        os.close(fd)
        os.unlink(fname)

    def test_undirected(self):
        self.pydot_checks(nx.Graph(), prog="neato")

    def test_directed(self):
        self.pydot_checks(nx.DiGraph(), prog="dot")

    def test_read_write(self):
        G = nx.MultiGraph()
        G.graph["name"] = "G"
        G.add_edge("1", "2", key="0")  # read assumes strings
        fh = StringIO()
        nx.nx_pydot.write_dot(G, fh)
        fh.seek(0)
        H = nx.nx_pydot.read_dot(fh)
        assert graphs_equal(G, H)


def test_pydot_issue_258():
    G = nx.Graph([("Example:A", 1)])
    with pytest.raises(ValueError):
        nx.nx_pydot.to_pydot(G)
    with pytest.raises(ValueError):
        nx.nx_pydot.pydot_layout(G)

    G = nx.Graph()
    G.add_node("1.2", style="filled", fillcolor="red:yellow")
    with pytest.raises(ValueError):
        nx.nx_pydot.to_pydot(G)
    G.remove_node("1.2")
    G.add_node("1.2", style="filled", fillcolor='"red:yellow"')
    assert (
        G.nodes.data() == nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G)).nodes.data()
    )

    G = nx.DiGraph()
    G.add_edge("1", "2", foo="bar:1")
    with pytest.raises(ValueError):
        nx.nx_pydot.to_pydot(G)
    G = nx.DiGraph()
    G.add_edge("1", "2", foo='"bar:1"')
    assert G["1"]["2"] == nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G))["1"]["2"]

    G = nx.MultiGraph()
    G.add_edge("1", "2", foo="b:1")
    G.add_edge("1", "2", bar="foo:foo")
    with pytest.raises(ValueError):
        nx.nx_pydot.to_pydot(G)
    G = nx.MultiGraph()
    G.add_edge("1", "2", foo='"b:1"')
    G.add_edge("1", "2", bar='"foo:foo"')
    # Keys as integers aren't preserved in the conversion. They are read as strings.
    assert [attr for _, _, attr in G.edges.data()] == [
        attr
        for _, _, attr in nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G)).edges.data()
    ]

    G = nx.Graph()
    G.add_edge("1", "2")
    G["1"]["2"]["f:oo"] = "bar"
    with pytest.raises(ValueError):
        nx.nx_pydot.to_pydot(G)
    G = nx.Graph()
    G.add_edge("1", "2")
    G["1"]["2"]['"f:oo"'] = "bar"
    assert G["1"]["2"] == nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G))["1"]["2"]

    G = nx.Graph([('"Example:A"', 1)])
    layout = nx.nx_pydot.pydot_layout(G)
    assert isinstance(layout, dict)


@pytest.mark.parametrize(
    "graph_type", [nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph]
)
def test_hashable_pydot(graph_type):
    # gh-5790
    G = graph_type()
    G.add_edge("5", frozenset([1]), t='"Example:A"', l=False)
    G.add_edge("1", 2, w=True, t=("node1",), l=frozenset(["node1"]))
    G.add_edge("node", (3, 3), w="string")

    assert [
        {"t": '"Example:A"', "l": "False"},
        {"w": "True", "t": "('node1',)", "l": "frozenset({'node1'})"},
        {"w": "string"},
    ] == [
        attr
        for _, _, attr in nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G)).edges.data()
    ]

    assert {str(i) for i in G.nodes()} == set(
        nx.nx_pydot.from_pydot(nx.nx_pydot.to_pydot(G)).nodes
    )


def test_pydot_numerical_name():
    G = nx.Graph()
    G.add_edges_from([("A", "B"), (0, 1)])
    graph_layout = nx.nx_pydot.pydot_layout(G, prog="dot")
    assert isinstance(graph_layout, dict)
    assert "0" not in graph_layout
    assert 0 in graph_layout
    assert "1" not in graph_layout
    assert 1 in graph_layout
    assert "A" in graph_layout
    assert "B" in graph_layout
