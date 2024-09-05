from __future__ import annotations

import functools
from typing import TypeVar, Callable, Awaitable
from typing_extensions import ParamSpec

import anyio
import anyio.to_thread

from ._reflection import function_has_argument

T_Retval = TypeVar("T_Retval")
T_ParamSpec = ParamSpec("T_ParamSpec")


# copied from `asyncer`, https://github.com/tiangolo/asyncer
def asyncify(
    function: Callable[T_ParamSpec, T_Retval],
    *,
    cancellable: bool = False,
    limiter: anyio.CapacityLimiter | None = None,
) -> Callable[T_ParamSpec, Awaitable[T_Retval]]:
    """
    Take a blocking function and create an async one that receives the same
    positional and keyword arguments, and that when called, calls the original function
    in a worker thread using `anyio.to_thread.run_sync()`. Internally,
    `asyncer.asyncify()` uses the same `anyio.to_thread.run_sync()`, but it supports
    keyword arguments additional to positional arguments and it adds better support for
    autocompletion and inline errors for the arguments of the function called and the
    return value.

    If the `cancellable` option is enabled and the task waiting for its completion is
    cancelled, the thread will still run its course but its return value (or any raised
    exception) will be ignored.

    Use it like this:

    ```Python
    def do_work(arg1, arg2, kwarg1="", kwarg2="") -> str:
        # Do work
        return "Some result"


    result = await to_thread.asyncify(do_work)("spam", "ham", kwarg1="a", kwarg2="b")
    print(result)
    ```

    ## Arguments

    `function`: a blocking regular callable (e.g. a function)
    `cancellable`: `True` to allow cancellation of the operation
    `limiter`: capacity limiter to use to limit the total amount of threads running
        (if omitted, the default limiter is used)

    ## Return

    An async function that takes the same positional and keyword arguments as the
    original one, that when called runs the same original function in a thread worker
    and returns the result.
    """

    async def wrapper(*args: T_ParamSpec.args, **kwargs: T_ParamSpec.kwargs) -> T_Retval:
        partial_f = functools.partial(function, *args, **kwargs)

        # In `v4.1.0` anyio added the `abandon_on_cancel` argument and deprecated the old
        # `cancellable` argument, so we need to use the new `abandon_on_cancel` to avoid
        # surfacing deprecation warnings.
        if function_has_argument(anyio.to_thread.run_sync, "abandon_on_cancel"):
            return await anyio.to_thread.run_sync(
                partial_f,
                abandon_on_cancel=cancellable,
                limiter=limiter,
            )

        return await anyio.to_thread.run_sync(
            partial_f,
            cancellable=cancellable,
            limiter=limiter,
        )

    return wrapper
