# This file contains utilities for testing the dispatching feature

# A full test of all dispatchable algorithms is performed by
# modifying the pytest invocation and setting an environment variable
# NETWORKX_TEST_BACKEND=nx-loopback pytest
# This is comprehensive, but only tests the `test_override_dispatch`
# function in networkx.classes.backends.

# To test the `_dispatch` function directly, several tests scattered throughout
# NetworkX have been augmented to test normal and dispatch mode.
# Searching for `dispatch_interface` should locate the specific tests.

import networkx as nx
from networkx import DiGraph, Graph, MultiDiGraph, MultiGraph, PlanarEmbedding
from networkx.classes.reportviews import NodeView


class LoopbackGraph(Graph):
    __networkx_backend__ = "nx-loopback"


class LoopbackDiGraph(DiGraph):
    __networkx_backend__ = "nx-loopback"


class LoopbackMultiGraph(MultiGraph):
    __networkx_backend__ = "nx-loopback"


class LoopbackMultiDiGraph(MultiDiGraph):
    __networkx_backend__ = "nx-loopback"


class LoopbackPlanarEmbedding(PlanarEmbedding):
    __networkx_backend__ = "nx-loopback"


def convert(graph):
    if isinstance(graph, PlanarEmbedding):
        return LoopbackPlanarEmbedding(graph)
    if isinstance(graph, MultiDiGraph):
        return LoopbackMultiDiGraph(graph)
    if isinstance(graph, MultiGraph):
        return LoopbackMultiGraph(graph)
    if isinstance(graph, DiGraph):
        return LoopbackDiGraph(graph)
    if isinstance(graph, Graph):
        return LoopbackGraph(graph)
    raise TypeError(f"Unsupported type of graph: {type(graph)}")


class LoopbackDispatcher:
    def __getattr__(self, item):
        try:
            return nx.utils.backends._registered_algorithms[item].orig_func
        except KeyError:
            raise AttributeError(item) from None

    @staticmethod
    def convert_from_nx(
        graph,
        *,
        edge_attrs=None,
        node_attrs=None,
        preserve_edge_attrs=None,
        preserve_node_attrs=None,
        preserve_graph_attrs=None,
        name=None,
        graph_name=None,
    ):
        if name in {
            # Raise if input graph changes
            "lexicographical_topological_sort",
            "topological_generations",
            "topological_sort",
            # Sensitive tests (iteration order matters)
            "dfs_labeled_edges",
        }:
            return graph
        if isinstance(graph, NodeView):
            # Convert to a Graph with only nodes (no edges)
            new_graph = Graph()
            new_graph.add_nodes_from(graph.items())
            graph = new_graph
            G = LoopbackGraph()
        elif not isinstance(graph, Graph):
            raise TypeError(
                f"Bad type for graph argument {graph_name} in {name}: {type(graph)}"
            )
        elif graph.__class__ in {Graph, LoopbackGraph}:
            G = LoopbackGraph()
        elif graph.__class__ in {DiGraph, LoopbackDiGraph}:
            G = LoopbackDiGraph()
        elif graph.__class__ in {MultiGraph, LoopbackMultiGraph}:
            G = LoopbackMultiGraph()
        elif graph.__class__ in {MultiDiGraph, LoopbackMultiDiGraph}:
            G = LoopbackMultiDiGraph()
        elif graph.__class__ in {PlanarEmbedding, LoopbackPlanarEmbedding}:
            G = LoopbackDiGraph()  # or LoopbackPlanarEmbedding
        else:
            # It would be nice to be able to convert _AntiGraph to a regular Graph
            # nx.algorithms.approximation.kcomponents._AntiGraph
            # nx.algorithms.tree.branchings.MultiDiGraph_EdgeKey
            # nx.classes.tests.test_multidigraph.MultiDiGraphSubClass
            # nx.classes.tests.test_multigraph.MultiGraphSubClass
            G = graph.__class__()

        if preserve_graph_attrs:
            G.graph.update(graph.graph)

        if preserve_node_attrs:
            G.add_nodes_from(graph.nodes(data=True))
        elif node_attrs:
            G.add_nodes_from(
                (
                    node,
                    {
                        k: datadict.get(k, default)
                        for k, default in node_attrs.items()
                        if default is not None or k in datadict
                    },
                )
                for node, datadict in graph.nodes(data=True)
            )
        else:
            G.add_nodes_from(graph)

        if graph.is_multigraph():
            if preserve_edge_attrs:
                G.add_edges_from(
                    (u, v, key, datadict)
                    for u, nbrs in graph._adj.items()
                    for v, keydict in nbrs.items()
                    for key, datadict in keydict.items()
                )
            elif edge_attrs:
                G.add_edges_from(
                    (
                        u,
                        v,
                        key,
                        {
                            k: datadict.get(k, default)
                            for k, default in edge_attrs.items()
                            if default is not None or k in datadict
                        },
                    )
                    for u, nbrs in graph._adj.items()
                    for v, keydict in nbrs.items()
                    for key, datadict in keydict.items()
                )
            else:
                G.add_edges_from(
                    (u, v, key, {})
                    for u, nbrs in graph._adj.items()
                    for v, keydict in nbrs.items()
                    for key, datadict in keydict.items()
                )
        elif preserve_edge_attrs:
            G.add_edges_from(graph.edges(data=True))
        elif edge_attrs:
            G.add_edges_from(
                (
                    u,
                    v,
                    {
                        k: datadict.get(k, default)
                        for k, default in edge_attrs.items()
                        if default is not None or k in datadict
                    },
                )
                for u, v, datadict in graph.edges(data=True)
            )
        else:
            G.add_edges_from(graph.edges)
        return G

    @staticmethod
    def convert_to_nx(obj, *, name=None):
        return obj

    @staticmethod
    def on_start_tests(items):
        # Verify that items can be xfailed
        for item in items:
            assert hasattr(item, "add_marker")

    def can_run(self, name, args, kwargs):
        # It is unnecessary to define this function if algorithms are fully supported.
        # We include it for illustration purposes.
        return hasattr(self, name)


dispatcher = LoopbackDispatcher()
