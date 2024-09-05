import networkx as nx

__all__ = ["s_metric"]


@nx._dispatch
def s_metric(G, **kwargs):
    """Returns the s-metric [1]_ of graph.

    The s-metric is defined as the sum of the products ``deg(u) * deg(v)``
    for every edge ``(u, v)`` in `G`.

    Parameters
    ----------
    G : graph
        The graph used to compute the s-metric.
    normalized : bool (optional)
        Normalize the value.

        .. deprecated:: 3.2

           The `normalized` keyword argument is deprecated and will be removed
           in the future

    Returns
    -------
    s : float
        The s-metric of the graph.

    References
    ----------
    .. [1] Lun Li, David Alderson, John C. Doyle, and Walter Willinger,
           Towards a Theory of Scale-Free Graphs:
           Definition, Properties, and  Implications (Extended Version), 2005.
           https://arxiv.org/abs/cond-mat/0501169
    """
    # NOTE: This entire code block + the **kwargs in the signature can all be
    # removed when the deprecation expires.
    # Normalized is always False, since all `normalized=True` did was raise
    # a NotImplementedError
    if kwargs:
        # Warn for `normalize`, raise for any other kwarg
        if "normalized" in kwargs:
            import warnings

            warnings.warn(
                "\n\nThe `normalized` keyword is deprecated and will be removed\n"
                "in the future. To silence this warning, remove `normalized`\n"
                "when calling `s_metric`.\n\n"
                "The value of `normalized` is ignored.",
                DeprecationWarning,
                stacklevel=3,
            )
        else:
            # Typical raising behavior for Python when kwarg not recognized
            raise TypeError(
                f"s_metric got an unexpected keyword argument '{list(kwargs.keys())[0]}'"
            )

    return float(sum(G.degree(u) * G.degree(v) for (u, v) in G.edges()))
