from __future__ import annotations as _annotations

import inspect
from functools import partial
from typing import Any, Awaitable, Callable

import pydantic_core

from ..config import ConfigDict
from ..plugin._schema_validator import create_schema_validator
from . import _generate_schema, _typing_extra
from ._config import ConfigWrapper


class ValidateCallWrapper:
    """This is a wrapper around a function that validates the arguments passed to it, and optionally the return value."""

    __slots__ = (
        '__pydantic_validator__',
        '__name__',
        '__qualname__',
        '__annotations__',
        '__dict__',  # required for __module__
    )

    def __init__(
        self,
        function: Callable[..., Any],
        config: ConfigDict | None,
        validate_return: bool,
        namespace: dict[str, Any] | None,
    ):
        if isinstance(function, partial):
            func = function.func
            schema_type = func
            self.__name__ = f'partial({func.__name__})'
            self.__qualname__ = f'partial({func.__qualname__})'
            self.__module__ = func.__module__
        else:
            schema_type = function
            self.__name__ = function.__name__
            self.__qualname__ = function.__qualname__
            self.__module__ = function.__module__

        global_ns = _typing_extra.add_module_globals(function, None)
        # TODO: this is a bit of a hack, we should probably have a better way to handle this
        # specifically, we shouldn't be pumping the namespace full of type_params
        # when we take namespace and type_params arguments in eval_type_backport
        type_params = getattr(schema_type, '__type_params__', ())
        namespace = {
            **{param.__name__: param for param in type_params},
            **(global_ns or {}),
            **(namespace or {}),
        }
        config_wrapper = ConfigWrapper(config)
        gen_schema = _generate_schema.GenerateSchema(config_wrapper, namespace)
        schema = gen_schema.clean_schema(gen_schema.generate_schema(function))
        core_config = config_wrapper.core_config(self)

        self.__pydantic_validator__ = create_schema_validator(
            schema,
            schema_type,
            self.__module__,
            self.__qualname__,
            'validate_call',
            core_config,
            config_wrapper.plugin_settings,
        )

        if validate_return:
            signature = inspect.signature(function)
            return_type = signature.return_annotation if signature.return_annotation is not signature.empty else Any
            gen_schema = _generate_schema.GenerateSchema(config_wrapper, namespace)
            schema = gen_schema.clean_schema(gen_schema.generate_schema(return_type))
            validator = create_schema_validator(
                schema,
                schema_type,
                self.__module__,
                self.__qualname__,
                'validate_call',
                core_config,
                config_wrapper.plugin_settings,
            )
            if inspect.iscoroutinefunction(function):

                async def return_val_wrapper(aw: Awaitable[Any]) -> None:
                    return validator.validate_python(await aw)

                self.__return_pydantic_validator__ = return_val_wrapper
            else:
                self.__return_pydantic_validator__ = validator.validate_python
        else:
            self.__return_pydantic_validator__ = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        res = self.__pydantic_validator__.validate_python(pydantic_core.ArgsKwargs(args, kwargs))
        if self.__return_pydantic_validator__:
            return self.__return_pydantic_validator__(res)
        return res
