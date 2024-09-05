import warnings

import pytest

import networkx as nx


def test_smetric():
    g = nx.Graph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)
    g.add_edge(1, 4)
    sm = nx.s_metric(g, normalized=False)
    assert sm == 19.0


# NOTE: Tests below to be deleted when deprecation of `normalized` kwarg expires


def test_normalized_deprecation_warning():
    """Test that a deprecation warning is raised when s_metric is called with
    a `normalized` kwarg."""
    G = nx.cycle_graph(7)
    # No warning raised when called without kwargs (future behavior)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Fail the test if warning caught
        assert nx.s_metric(G) == 28

    # Deprecation warning
    with pytest.deprecated_call():
        nx.s_metric(G, normalized=True)

    # Make sure you get standard Python behavior when unrecognized keyword provided
    with pytest.raises(TypeError):
        nx.s_metric(G, normalize=True)
