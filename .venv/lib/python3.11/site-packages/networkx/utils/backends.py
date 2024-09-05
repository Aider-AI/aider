"""
Code to support various backends in a plugin dispatch architecture.

Create a Dispatcher
-------------------

To be a valid backend, a package must register an entry_point
of `networkx.backends` with a key pointing to the handler.

For example::

    entry_points={'networkx.backends': 'sparse = networkx_backend_sparse'}

The backend must create a Graph-like object which contains an attribute
``__networkx_backend__`` with a value of the entry point name.

Continuing the example above::

    class WrappedSparse:
        __networkx_backend__ = "sparse"
        ...

When a dispatchable NetworkX algorithm encounters a Graph-like object
with a ``__networkx_backend__`` attribute, it will look for the associated
dispatch object in the entry_points, load it, and dispatch the work to it.


Testing
-------
To assist in validating the backend algorithm implementations, if an
environment variable ``NETWORKX_TEST_BACKEND`` is set to a registered
backend key, the dispatch machinery will automatically convert regular
networkx Graphs and DiGraphs to the backend equivalent by calling
``<backend dispatcher>.convert_from_nx(G, edge_attrs=edge_attrs, name=name)``.
Set ``NETWORKX_FALLBACK_TO_NX`` environment variable to have tests
use networkx graphs for algorithms not implemented by the backend.

The arguments to ``convert_from_nx`` are:

- ``G`` : networkx Graph
- ``edge_attrs`` : dict, optional
    Dict that maps edge attributes to default values if missing in ``G``.
    If None, then no edge attributes will be converted and default may be 1.
- ``node_attrs``: dict, optional
    Dict that maps node attribute to default values if missing in ``G``.
    If None, then no node attributes will be converted.
- ``preserve_edge_attrs`` : bool
    Whether to preserve all edge attributes.
- ``preserve_node_attrs`` : bool
    Whether to preserve all node attributes.
- ``preserve_graph_attrs`` : bool
    Whether to preserve all graph attributes.
- ``preserve_all_attrs`` : bool
    Whether to preserve all graph, node, and edge attributes.
- ``name`` : str
    The name of the algorithm.
- ``graph_name`` : str
    The name of the graph argument being converted.

The converted object is then passed to the backend implementation of
the algorithm. The result is then passed to
``<backend dispatcher>.convert_to_nx(result, name=name)`` to convert back
to a form expected by the NetworkX tests.

By defining ``convert_from_nx`` and ``convert_to_nx`` methods and setting
the environment variable, NetworkX will automatically route tests on
dispatchable algorithms to the backend, allowing the full networkx test
suite to be run against the backend implementation.

Example pytest invocation::

    NETWORKX_TEST_BACKEND=sparse pytest --pyargs networkx

Dispatchable algorithms which are not implemented by the backend
will cause a ``pytest.xfail()``, giving some indication that not all
tests are working, while avoiding causing an explicit failure.

If a backend only partially implements some algorithms, it can define
a ``can_run(name, args, kwargs)`` function that returns True or False
indicating whether it can run the algorithm with the given arguments.

A special ``on_start_tests(items)`` function may be defined by the backend.
It will be called with the list of NetworkX tests discovered. Each item
is a test object that can be marked as xfail if the backend does not support
the test using `item.add_marker(pytest.mark.xfail(reason=...))`.
"""
import inspect
import os
import sys
import warnings
from functools import partial
from importlib.metadata import entry_points

from ..exception import NetworkXNotImplemented

__all__ = ["_dispatch"]


def _get_backends(group, *, load_and_call=False):
    if sys.version_info < (3, 10):
        eps = entry_points()
        if group not in eps:
            return {}
        items = eps[group]
    else:
        items = entry_points(group=group)
    rv = {}
    for ep in items:
        if ep.name in rv:
            warnings.warn(
                f"networkx backend defined more than once: {ep.name}",
                RuntimeWarning,
                stacklevel=2,
            )
        elif load_and_call:
            try:
                rv[ep.name] = ep.load()()
            except Exception as exc:
                warnings.warn(
                    f"Error encountered when loading info for backend {ep.name}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        else:
            rv[ep.name] = ep
    # nx-loopback backend is only available when testing (added in conftest.py)
    rv.pop("nx-loopback", None)
    return rv


# Rename "plugin" to "backend", and give backends a release cycle to update.
backends = _get_backends("networkx.plugins")
backend_info = _get_backends("networkx.plugin_info", load_and_call=True)

backends.update(_get_backends("networkx.backends"))
backend_info.update(_get_backends("networkx.backend_info", load_and_call=True))

# Load and cache backends on-demand
_loaded_backends = {}  # type: ignore[var-annotated]


def _load_backend(backend_name):
    if backend_name in _loaded_backends:
        return _loaded_backends[backend_name]
    rv = _loaded_backends[backend_name] = backends[backend_name].load()
    return rv


_registered_algorithms = {}


class _dispatch:
    """Dispatches to a backend algorithm based on input graph types.

    Parameters
    ----------
    func : function

    name : str, optional
        The name of the algorithm to use for dispatching. If not provided,
        the name of ``func`` will be used. ``name`` is useful to avoid name
        conflicts, as all dispatched algorithms live in a single namespace.

    graphs : str or dict or None, default "G"
        If a string, the parameter name of the graph, which must be the first
        argument of the wrapped function. If more than one graph is required
        for the algorithm (or if the graph is not the first argument), provide
        a dict of parameter name to argument position for each graph argument.
        For example, ``@_dispatch(graphs={"G": 0, "auxiliary?": 4})``
        indicates the 0th parameter ``G`` of the function is a required graph,
        and the 4th parameter ``auxiliary`` is an optional graph.
        To indicate an argument is a list of graphs, do e.g. ``"[graphs]"``.
        Use ``graphs=None`` if *no* arguments are NetworkX graphs such as for
        graph generators, readers, and conversion functions.

    edge_attrs : str or dict, optional
        ``edge_attrs`` holds information about edge attribute arguments
        and default values for those edge attributes.
        If a string, ``edge_attrs`` holds the function argument name that
        indicates a single edge attribute to include in the converted graph.
        The default value for this attribute is 1. To indicate that an argument
        is a list of attributes (all with default value 1), use e.g. ``"[attrs]"``.
        If a dict, ``edge_attrs`` holds a dict keyed by argument names, with
        values that are either the default value or, if a string, the argument
        name that indicates the default value.

    node_attrs : str or dict, optional
        Like ``edge_attrs``, but for node attributes.

    preserve_edge_attrs : bool or str or dict, optional
        For bool, whether to preserve all edge attributes.
        For str, the parameter name that may indicate (with ``True`` or a
        callable argument) whether all edge attributes should be preserved
        when converting.
        For dict of ``{graph_name: {attr: default}}``, indicate pre-determined
        edge attributes (and defaults) to preserve for input graphs.

    preserve_node_attrs : bool or str or dict, optional
        Like ``preserve_edge_attrs``, but for node attributes.

    preserve_graph_attrs : bool or set
        For bool, whether to preserve all graph attributes.
        For set, which input graph arguments to preserve graph attributes.

    preserve_all_attrs : bool
        Whether to preserve all edge, node and graph attributes.
        This overrides all the other preserve_*_attrs.

    """

    # Allow any of the following decorator forms:
    #  - @_dispatch
    #  - @_dispatch()
    #  - @_dispatch(name="override_name")
    #  - @_dispatch(graphs="graph")
    #  - @_dispatch(edge_attrs="weight")
    #  - @_dispatch(graphs={"G": 0, "H": 1}, edge_attrs={"weight": "default"})

    # These class attributes are currently used to allow backends to run networkx tests.
    # For example: `PYTHONPATH=. pytest --backend graphblas --fallback-to-nx`
    # Future work: add configuration to control these
    _is_testing = False
    _fallback_to_nx = (
        os.environ.get("NETWORKX_FALLBACK_TO_NX", "true").strip().lower() == "true"
    )
    _automatic_backends = [
        x.strip()
        for x in os.environ.get("NETWORKX_AUTOMATIC_BACKENDS", "").split(",")
        if x.strip()
    ]

    def __new__(
        cls,
        func=None,
        *,
        name=None,
        graphs="G",
        edge_attrs=None,
        node_attrs=None,
        preserve_edge_attrs=False,
        preserve_node_attrs=False,
        preserve_graph_attrs=False,
        preserve_all_attrs=False,
    ):
        if func is None:
            return partial(
                _dispatch,
                name=name,
                graphs=graphs,
                edge_attrs=edge_attrs,
                node_attrs=node_attrs,
                preserve_edge_attrs=preserve_edge_attrs,
                preserve_node_attrs=preserve_node_attrs,
                preserve_graph_attrs=preserve_graph_attrs,
                preserve_all_attrs=preserve_all_attrs,
            )
        if isinstance(func, str):
            raise TypeError("'name' and 'graphs' must be passed by keyword") from None
        # If name not provided, use the name of the function
        if name is None:
            name = func.__name__

        self = object.__new__(cls)

        # standard function-wrapping stuff
        # __annotations__ not used
        self.__name__ = func.__name__
        # self.__doc__ = func.__doc__  # __doc__ handled as cached property
        self.__defaults__ = func.__defaults__
        # We "magically" add `backend=` keyword argument to allow backend to be specified
        if func.__kwdefaults__:
            self.__kwdefaults__ = {**func.__kwdefaults__, "backend": None}
        else:
            self.__kwdefaults__ = {"backend": None}
        self.__module__ = func.__module__
        self.__qualname__ = func.__qualname__
        self.__dict__.update(func.__dict__)
        self.__wrapped__ = func

        # Supplement docstring with backend info; compute and cache when needed
        self._orig_doc = func.__doc__
        self._cached_doc = None

        self.orig_func = func
        self.name = name
        self.edge_attrs = edge_attrs
        self.node_attrs = node_attrs
        self.preserve_edge_attrs = preserve_edge_attrs or preserve_all_attrs
        self.preserve_node_attrs = preserve_node_attrs or preserve_all_attrs
        self.preserve_graph_attrs = preserve_graph_attrs or preserve_all_attrs

        if edge_attrs is not None and not isinstance(edge_attrs, (str, dict)):
            raise TypeError(
                f"Bad type for edge_attrs: {type(edge_attrs)}. Expected str or dict."
            ) from None
        if node_attrs is not None and not isinstance(node_attrs, (str, dict)):
            raise TypeError(
                f"Bad type for node_attrs: {type(node_attrs)}. Expected str or dict."
            ) from None
        if not isinstance(self.preserve_edge_attrs, (bool, str, dict)):
            raise TypeError(
                f"Bad type for preserve_edge_attrs: {type(self.preserve_edge_attrs)}."
                " Expected bool, str, or dict."
            ) from None
        if not isinstance(self.preserve_node_attrs, (bool, str, dict)):
            raise TypeError(
                f"Bad type for preserve_node_attrs: {type(self.preserve_node_attrs)}."
                " Expected bool, str, or dict."
            ) from None
        if not isinstance(self.preserve_graph_attrs, (bool, set)):
            raise TypeError(
                f"Bad type for preserve_graph_attrs: {type(self.preserve_graph_attrs)}."
                " Expected bool or set."
            ) from None

        if isinstance(graphs, str):
            graphs = {graphs: 0}
        elif graphs is None:
            pass
        elif not isinstance(graphs, dict):
            raise TypeError(
                f"Bad type for graphs: {type(graphs)}. Expected str or dict."
            ) from None
        elif len(graphs) == 0:
            raise KeyError("'graphs' must contain at least one variable name") from None

        # This dict comprehension is complicated for better performance; equivalent shown below.
        self.optional_graphs = set()
        self.list_graphs = set()
        if graphs is None:
            self.graphs = {}
        else:
            self.graphs = {
                self.optional_graphs.add(val := k[:-1]) or val
                if (last := k[-1]) == "?"
                else self.list_graphs.add(val := k[1:-1]) or val
                if last == "]"
                else k: v
                for k, v in graphs.items()
            }
        # The above is equivalent to:
        # self.optional_graphs = {k[:-1] for k in graphs if k[-1] == "?"}
        # self.list_graphs = {k[1:-1] for k in graphs if k[-1] == "]"}
        # self.graphs = {k[:-1] if k[-1] == "?" else k: v for k, v in graphs.items()}

        # Compute and cache the signature on-demand
        self._sig = None

        # Which backends implement this function?
        self.backends = {
            backend
            for backend, info in backend_info.items()
            if "functions" in info and name in info["functions"]
        }

        if name in _registered_algorithms:
            raise KeyError(
                f"Algorithm already exists in dispatch registry: {name}"
            ) from None
        _registered_algorithms[name] = self
        return self

    @property
    def __doc__(self):
        if (rv := self._cached_doc) is not None:
            return rv
        rv = self._cached_doc = self._make_doc()
        return rv

    @__doc__.setter
    def __doc__(self, val):
        self._orig_doc = val
        self._cached_doc = None

    @property
    def __signature__(self):
        if self._sig is None:
            sig = inspect.signature(self.orig_func)
            # `backend` is now a reserved argument used by dispatching.
            # assert "backend" not in sig.parameters
            if not any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                sig = sig.replace(
                    parameters=[
                        *sig.parameters.values(),
                        inspect.Parameter(
                            "backend", inspect.Parameter.KEYWORD_ONLY, default=None
                        ),
                        inspect.Parameter(
                            "backend_kwargs", inspect.Parameter.VAR_KEYWORD
                        ),
                    ]
                )
            else:
                *parameters, var_keyword = sig.parameters.values()
                sig = sig.replace(
                    parameters=[
                        *parameters,
                        inspect.Parameter(
                            "backend", inspect.Parameter.KEYWORD_ONLY, default=None
                        ),
                        var_keyword,
                    ]
                )
            self._sig = sig
        return self._sig

    def __call__(self, /, *args, backend=None, **kwargs):
        if not backends:
            # Fast path if no backends are installed
            return self.orig_func(*args, **kwargs)

        # Use `backend_name` in this function instead of `backend`
        backend_name = backend
        if backend_name is not None and backend_name not in backends:
            raise ImportError(f"Unable to load backend: {backend_name}")

        graphs_resolved = {}
        for gname, pos in self.graphs.items():
            if pos < len(args):
                if gname in kwargs:
                    raise TypeError(f"{self.name}() got multiple values for {gname!r}")
                val = args[pos]
            elif gname in kwargs:
                val = kwargs[gname]
            elif gname not in self.optional_graphs:
                raise TypeError(
                    f"{self.name}() missing required graph argument: {gname}"
                )
            else:
                continue
            if val is None:
                if gname not in self.optional_graphs:
                    raise TypeError(
                        f"{self.name}() required graph argument {gname!r} is None; must be a graph"
                    )
            else:
                graphs_resolved[gname] = val

        # Alternative to the above that does not check duplicated args or missing required graphs.
        # graphs_resolved = {
        #     val
        #     for gname, pos in self.graphs.items()
        #     if (val := args[pos] if pos < len(args) else kwargs.get(gname)) is not None
        # }

        if self._is_testing and self._automatic_backends and backend_name is None:
            # Special path if we are running networkx tests with a backend.
            return self._convert_and_call_for_tests(
                self._automatic_backends[0],
                args,
                kwargs,
                fallback_to_nx=self._fallback_to_nx,
            )

        # Check if any graph comes from a backend
        if self.list_graphs:
            # Make sure we don't lose values by consuming an iterator
            args = list(args)
            for gname in self.list_graphs & graphs_resolved.keys():
                val = list(graphs_resolved[gname])
                graphs_resolved[gname] = val
                if gname in kwargs:
                    kwargs[gname] = val
                else:
                    args[self.graphs[gname]] = val

            has_backends = any(
                hasattr(g, "__networkx_backend__") or hasattr(g, "__networkx_plugin__")
                if gname not in self.list_graphs
                else any(
                    hasattr(g2, "__networkx_backend__")
                    or hasattr(g2, "__networkx_plugin__")
                    for g2 in g
                )
                for gname, g in graphs_resolved.items()
            )
            if has_backends:
                graph_backend_names = {
                    getattr(
                        g,
                        "__networkx_backend__",
                        getattr(g, "__networkx_plugin__", "networkx"),
                    )
                    for gname, g in graphs_resolved.items()
                    if gname not in self.list_graphs
                }
                for gname in self.list_graphs & graphs_resolved.keys():
                    graph_backend_names.update(
                        getattr(
                            g,
                            "__networkx_backend__",
                            getattr(g, "__networkx_plugin__", "networkx"),
                        )
                        for g in graphs_resolved[gname]
                    )
        else:
            has_backends = any(
                hasattr(g, "__networkx_backend__") or hasattr(g, "__networkx_plugin__")
                for g in graphs_resolved.values()
            )
            if has_backends:
                graph_backend_names = {
                    getattr(
                        g,
                        "__networkx_backend__",
                        getattr(g, "__networkx_plugin__", "networkx"),
                    )
                    for g in graphs_resolved.values()
                }
        if has_backends:
            # Dispatchable graphs found! Dispatch to backend function.
            # We don't handle calls with different backend graphs yet,
            # but we may be able to convert additional networkx graphs.
            backend_names = graph_backend_names - {"networkx"}
            if len(backend_names) != 1:
                # Future work: convert between backends and run if multiple backends found
                raise TypeError(
                    f"{self.name}() graphs must all be from the same backend, found {backend_names}"
                )
            [graph_backend_name] = backend_names
            if backend_name is not None and backend_name != graph_backend_name:
                # Future work: convert between backends to `backend_name` backend
                raise TypeError(
                    f"{self.name}() is unable to convert graph from backend {graph_backend_name!r} "
                    f"to the specified backend {backend_name!r}."
                )
            if graph_backend_name not in backends:
                raise ImportError(f"Unable to load backend: {graph_backend_name}")
            if (
                "networkx" in graph_backend_names
                and graph_backend_name not in self._automatic_backends
            ):
                # Not configured to convert networkx graphs to this backend
                raise TypeError(
                    f"Unable to convert inputs and run {self.name}. "
                    f"{self.name}() has networkx and {graph_backend_name} graphs, but NetworkX is not "
                    f"configured to automatically convert graphs from networkx to {graph_backend_name}."
                )
            backend = _load_backend(graph_backend_name)
            if hasattr(backend, self.name):
                if "networkx" in graph_backend_names:
                    # We need to convert networkx graphs to backend graphs
                    return self._convert_and_call(
                        graph_backend_name,
                        args,
                        kwargs,
                        fallback_to_nx=self._fallback_to_nx,
                    )
                # All graphs are backend graphs--no need to convert!
                return getattr(backend, self.name)(*args, **kwargs)
            # Future work: try to convert and run with other backends in self._automatic_backends
            raise NetworkXNotImplemented(
                f"'{self.name}' not implemented by {graph_backend_name}"
            )

        # If backend was explicitly given by the user, so we need to use it no matter what
        if backend_name is not None:
            return self._convert_and_call(
                backend_name, args, kwargs, fallback_to_nx=False
            )

        # Only networkx graphs; try to convert and run with a backend with automatic
        # conversion, but don't do this by default for graph generators or loaders.
        if self.graphs:
            for backend_name in self._automatic_backends:
                if self._can_backend_run(backend_name, *args, **kwargs):
                    return self._convert_and_call(
                        backend_name,
                        args,
                        kwargs,
                        fallback_to_nx=self._fallback_to_nx,
                    )
        # Default: run with networkx on networkx inputs
        return self.orig_func(*args, **kwargs)

    def _can_backend_run(self, backend_name, /, *args, **kwargs):
        """Can the specified backend run this algorithms with these arguments?"""
        backend = _load_backend(backend_name)
        return hasattr(backend, self.name) and (
            not hasattr(backend, "can_run") or backend.can_run(self.name, args, kwargs)
        )

    def _convert_arguments(self, backend_name, args, kwargs):
        """Convert graph arguments to the specified backend.

        Returns
        -------
        args tuple and kwargs dict
        """
        bound = self.__signature__.bind(*args, **kwargs)
        bound.apply_defaults()
        if not self.graphs:
            bound_kwargs = bound.kwargs
            del bound_kwargs["backend"]
            return bound.args, bound_kwargs
        # Convert graphs into backend graph-like object
        # Include the edge and/or node labels if provided to the algorithm
        preserve_edge_attrs = self.preserve_edge_attrs
        edge_attrs = self.edge_attrs
        if preserve_edge_attrs is False:
            # e.g. `preserve_edge_attrs=False`
            pass
        elif preserve_edge_attrs is True:
            # e.g. `preserve_edge_attrs=True`
            edge_attrs = None
        elif isinstance(preserve_edge_attrs, str):
            if bound.arguments[preserve_edge_attrs] is True or callable(
                bound.arguments[preserve_edge_attrs]
            ):
                # e.g. `preserve_edge_attrs="attr"` and `func(attr=True)`
                # e.g. `preserve_edge_attrs="attr"` and `func(attr=myfunc)`
                preserve_edge_attrs = True
                edge_attrs = None
            elif bound.arguments[preserve_edge_attrs] is False and (
                isinstance(edge_attrs, str)
                and edge_attrs == preserve_edge_attrs
                or isinstance(edge_attrs, dict)
                and preserve_edge_attrs in edge_attrs
            ):
                # e.g. `preserve_edge_attrs="attr"` and `func(attr=False)`
                # Treat `False` argument as meaning "preserve_edge_data=False"
                # and not `False` as the edge attribute to use.
                preserve_edge_attrs = False
                edge_attrs = None
            else:
                # e.g. `preserve_edge_attrs="attr"` and `func(attr="weight")`
                preserve_edge_attrs = False
        # Else: e.g. `preserve_edge_attrs={"G": {"weight": 1}}`

        if edge_attrs is None:
            # May have been set to None above b/c all attributes are preserved
            pass
        elif isinstance(edge_attrs, str):
            if edge_attrs[0] == "[":
                # e.g. `edge_attrs="[edge_attributes]"` (argument of list of attributes)
                # e.g. `func(edge_attributes=["foo", "bar"])`
                edge_attrs = {
                    edge_attr: 1 for edge_attr in bound.arguments[edge_attrs[1:-1]]
                }
            elif callable(bound.arguments[edge_attrs]):
                # e.g. `edge_attrs="weight"` and `func(weight=myfunc)`
                preserve_edge_attrs = True
                edge_attrs = None
            elif bound.arguments[edge_attrs] is not None:
                # e.g. `edge_attrs="weight"` and `func(weight="foo")` (default of 1)
                edge_attrs = {bound.arguments[edge_attrs]: 1}
            elif self.name == "to_numpy_array" and hasattr(
                bound.arguments["dtype"], "names"
            ):
                # Custom handling: attributes may be obtained from `dtype`
                edge_attrs = {
                    edge_attr: 1 for edge_attr in bound.arguments["dtype"].names
                }
            else:
                # e.g. `edge_attrs="weight"` and `func(weight=None)`
                edge_attrs = None
        else:
            # e.g. `edge_attrs={"attr": "default"}` and `func(attr="foo", default=7)`
            # e.g. `edge_attrs={"attr": 0}` and `func(attr="foo")`
            edge_attrs = {
                edge_attr: bound.arguments.get(val, 1) if isinstance(val, str) else val
                for key, val in edge_attrs.items()
                if (edge_attr := bound.arguments[key]) is not None
            }

        preserve_node_attrs = self.preserve_node_attrs
        node_attrs = self.node_attrs
        if preserve_node_attrs is False:
            # e.g. `preserve_node_attrs=False`
            pass
        elif preserve_node_attrs is True:
            # e.g. `preserve_node_attrs=True`
            node_attrs = None
        elif isinstance(preserve_node_attrs, str):
            if bound.arguments[preserve_node_attrs] is True or callable(
                bound.arguments[preserve_node_attrs]
            ):
                # e.g. `preserve_node_attrs="attr"` and `func(attr=True)`
                # e.g. `preserve_node_attrs="attr"` and `func(attr=myfunc)`
                preserve_node_attrs = True
                node_attrs = None
            elif bound.arguments[preserve_node_attrs] is False and (
                isinstance(node_attrs, str)
                and node_attrs == preserve_node_attrs
                or isinstance(node_attrs, dict)
                and preserve_node_attrs in node_attrs
            ):
                # e.g. `preserve_node_attrs="attr"` and `func(attr=False)`
                # Treat `False` argument as meaning "preserve_node_data=False"
                # and not `False` as the node attribute to use. Is this used?
                preserve_node_attrs = False
                node_attrs = None
            else:
                # e.g. `preserve_node_attrs="attr"` and `func(attr="weight")`
                preserve_node_attrs = False
        # Else: e.g. `preserve_node_attrs={"G": {"pos": None}}`

        if node_attrs is None:
            # May have been set to None above b/c all attributes are preserved
            pass
        elif isinstance(node_attrs, str):
            if node_attrs[0] == "[":
                # e.g. `node_attrs="[node_attributes]"` (argument of list of attributes)
                # e.g. `func(node_attributes=["foo", "bar"])`
                node_attrs = {
                    node_attr: None for node_attr in bound.arguments[node_attrs[1:-1]]
                }
            elif callable(bound.arguments[node_attrs]):
                # e.g. `node_attrs="weight"` and `func(weight=myfunc)`
                preserve_node_attrs = True
                node_attrs = None
            elif bound.arguments[node_attrs] is not None:
                # e.g. `node_attrs="weight"` and `func(weight="foo")`
                node_attrs = {bound.arguments[node_attrs]: None}
            else:
                # e.g. `node_attrs="weight"` and `func(weight=None)`
                node_attrs = None
        else:
            # e.g. `node_attrs={"attr": "default"}` and `func(attr="foo", default=7)`
            # e.g. `node_attrs={"attr": 0}` and `func(attr="foo")`
            node_attrs = {
                node_attr: bound.arguments.get(val) if isinstance(val, str) else val
                for key, val in node_attrs.items()
                if (node_attr := bound.arguments[key]) is not None
            }

        preserve_graph_attrs = self.preserve_graph_attrs

        # It should be safe to assume that we either have networkx graphs or backend graphs.
        # Future work: allow conversions between backends.
        backend = _load_backend(backend_name)
        for gname in self.graphs:
            if gname in self.list_graphs:
                bound.arguments[gname] = [
                    backend.convert_from_nx(
                        g,
                        edge_attrs=edge_attrs,
                        node_attrs=node_attrs,
                        preserve_edge_attrs=preserve_edge_attrs,
                        preserve_node_attrs=preserve_node_attrs,
                        preserve_graph_attrs=preserve_graph_attrs,
                        name=self.name,
                        graph_name=gname,
                    )
                    if getattr(
                        g,
                        "__networkx_backend__",
                        getattr(g, "__networkx_plugin__", "networkx"),
                    )
                    == "networkx"
                    else g
                    for g in bound.arguments[gname]
                ]
            else:
                graph = bound.arguments[gname]
                if graph is None:
                    if gname in self.optional_graphs:
                        continue
                    raise TypeError(
                        f"Missing required graph argument `{gname}` in {self.name} function"
                    )
                if isinstance(preserve_edge_attrs, dict):
                    preserve_edges = False
                    edges = preserve_edge_attrs.get(gname, edge_attrs)
                else:
                    preserve_edges = preserve_edge_attrs
                    edges = edge_attrs
                if isinstance(preserve_node_attrs, dict):
                    preserve_nodes = False
                    nodes = preserve_node_attrs.get(gname, node_attrs)
                else:
                    preserve_nodes = preserve_node_attrs
                    nodes = node_attrs
                if isinstance(preserve_graph_attrs, set):
                    preserve_graph = gname in preserve_graph_attrs
                else:
                    preserve_graph = preserve_graph_attrs
                if (
                    getattr(
                        graph,
                        "__networkx_backend__",
                        getattr(graph, "__networkx_plugin__", "networkx"),
                    )
                    == "networkx"
                ):
                    bound.arguments[gname] = backend.convert_from_nx(
                        graph,
                        edge_attrs=edges,
                        node_attrs=nodes,
                        preserve_edge_attrs=preserve_edges,
                        preserve_node_attrs=preserve_nodes,
                        preserve_graph_attrs=preserve_graph,
                        name=self.name,
                        graph_name=gname,
                    )
        bound_kwargs = bound.kwargs
        del bound_kwargs["backend"]
        return bound.args, bound_kwargs

    def _convert_and_call(self, backend_name, args, kwargs, *, fallback_to_nx=False):
        """Call this dispatchable function with a backend, converting graphs if necessary."""
        backend = _load_backend(backend_name)
        if not self._can_backend_run(backend_name, *args, **kwargs):
            if fallback_to_nx:
                return self.orig_func(*args, **kwargs)
            msg = f"'{self.name}' not implemented by {backend_name}"
            if hasattr(backend, self.name):
                msg += " with the given arguments"
            raise RuntimeError(msg)

        try:
            converted_args, converted_kwargs = self._convert_arguments(
                backend_name, args, kwargs
            )
            result = getattr(backend, self.name)(*converted_args, **converted_kwargs)
        except (NotImplementedError, NetworkXNotImplemented) as exc:
            if fallback_to_nx:
                return self.orig_func(*args, **kwargs)
            raise

        return result

    def _convert_and_call_for_tests(
        self, backend_name, args, kwargs, *, fallback_to_nx=False
    ):
        """Call this dispatchable function with a backend; for use with testing."""
        backend = _load_backend(backend_name)
        if not self._can_backend_run(backend_name, *args, **kwargs):
            if fallback_to_nx or not self.graphs:
                return self.orig_func(*args, **kwargs)

            import pytest

            msg = f"'{self.name}' not implemented by {backend_name}"
            if hasattr(backend, self.name):
                msg += " with the given arguments"
            pytest.xfail(msg)

        try:
            converted_args, converted_kwargs = self._convert_arguments(
                backend_name, args, kwargs
            )
            result = getattr(backend, self.name)(*converted_args, **converted_kwargs)
        except (NotImplementedError, NetworkXNotImplemented) as exc:
            if fallback_to_nx:
                return self.orig_func(*args, **kwargs)
            import pytest

            pytest.xfail(
                exc.args[0] if exc.args else f"{self.name} raised {type(exc).__name__}"
            )

        if self.name in {
            "edmonds_karp_core",
            "barycenter",
            "contracted_nodes",
            "stochastic_graph",
            "relabel_nodes",
        }:
            # Special-case algorithms that mutate input graphs
            bound = self.__signature__.bind(*converted_args, **converted_kwargs)
            bound.apply_defaults()
            bound2 = self.__signature__.bind(*args, **kwargs)
            bound2.apply_defaults()
            if self.name == "edmonds_karp_core":
                R1 = backend.convert_to_nx(bound.arguments["R"])
                R2 = bound2.arguments["R"]
                for k, v in R1.edges.items():
                    R2.edges[k]["flow"] = v["flow"]
            elif self.name == "barycenter" and bound.arguments["attr"] is not None:
                G1 = backend.convert_to_nx(bound.arguments["G"])
                G2 = bound2.arguments["G"]
                attr = bound.arguments["attr"]
                for k, v in G1.nodes.items():
                    G2.nodes[k][attr] = v[attr]
            elif self.name == "contracted_nodes" and not bound.arguments["copy"]:
                # Edges and nodes changed; node "contraction" and edge "weight" attrs
                G1 = backend.convert_to_nx(bound.arguments["G"])
                G2 = bound2.arguments["G"]
                G2.__dict__.update(G1.__dict__)
            elif self.name == "stochastic_graph" and not bound.arguments["copy"]:
                G1 = backend.convert_to_nx(bound.arguments["G"])
                G2 = bound2.arguments["G"]
                for k, v in G1.edges.items():
                    G2.edges[k]["weight"] = v["weight"]
            elif self.name == "relabel_nodes" and not bound.arguments["copy"]:
                G1 = backend.convert_to_nx(bound.arguments["G"])
                G2 = bound2.arguments["G"]
                if G1 is G2:
                    return G2
                G2._node.clear()
                G2._node.update(G1._node)
                G2._adj.clear()
                G2._adj.update(G1._adj)
                if hasattr(G1, "_pred") and hasattr(G2, "_pred"):
                    G2._pred.clear()
                    G2._pred.update(G1._pred)
                if hasattr(G1, "_succ") and hasattr(G2, "_succ"):
                    G2._succ.clear()
                    G2._succ.update(G1._succ)
                return G2

        return backend.convert_to_nx(result, name=self.name)

    def _make_doc(self):
        if not self.backends:
            return self._orig_doc
        lines = [
            "Backends",
            "--------",
        ]
        for backend in sorted(self.backends):
            info = backend_info[backend]
            if "short_summary" in info:
                lines.append(f"{backend} : {info['short_summary']}")
            else:
                lines.append(backend)
            if "functions" not in info or self.name not in info["functions"]:
                lines.append("")
                continue

            func_info = info["functions"][self.name]
            if "extra_docstring" in func_info:
                lines.extend(
                    f"  {line}" if line else line
                    for line in func_info["extra_docstring"].split("\n")
                )
                add_gap = True
            else:
                add_gap = False
            if "extra_parameters" in func_info:
                if add_gap:
                    lines.append("")
                lines.append("  Extra parameters:")
                extra_parameters = func_info["extra_parameters"]
                for param in sorted(extra_parameters):
                    lines.append(f"    {param}")
                    if desc := extra_parameters[param]:
                        lines.append(f"      {desc}")
                    lines.append("")
            else:
                lines.append("")

        lines.pop()  # Remove last empty line
        to_add = "\n    ".join(lines)
        return f"{self._orig_doc.rstrip()}\n\n    {to_add}"

    def __reduce__(self):
        """Allow this object to be serialized with pickle.

        This uses the global registry `_registered_algorithms` to deserialize.
        """
        return _restore_dispatch, (self.name,)


def _restore_dispatch(name):
    return _registered_algorithms[name]


if os.environ.get("_NETWORKX_BUILDING_DOCS_"):
    # When building docs with Sphinx, use the original function with the
    # dispatched __doc__, b/c Sphinx renders normal Python functions better.
    # This doesn't show e.g. `*, backend=None, **backend_kwargs` in the
    # signatures, which is probably okay. It does allow the docstring to be
    # updated based on the installed backends.
    _orig_dispatch = _dispatch

    def _dispatch(func=None, **kwargs):  # type: ignore[no-redef]
        if func is None:
            return partial(_dispatch, **kwargs)
        dispatched_func = _orig_dispatch(func, **kwargs)
        func.__doc__ = dispatched_func.__doc__
        return func
