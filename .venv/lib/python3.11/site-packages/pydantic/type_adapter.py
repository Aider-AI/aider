"""Type adapter specification."""

from __future__ import annotations as _annotations

import sys
from contextlib import contextmanager
from dataclasses import is_dataclass
from functools import cached_property, wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Set,
    TypeVar,
    Union,
    cast,
    final,
    overload,
)

from pydantic_core import CoreSchema, SchemaSerializer, SchemaValidator, Some
from typing_extensions import Concatenate, ParamSpec, is_typeddict

from pydantic.errors import PydanticUserError
from pydantic.main import BaseModel

from ._internal import _config, _generate_schema, _mock_val_ser, _typing_extra, _utils
from .config import ConfigDict
from .json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaKeyT,
    JsonSchemaMode,
    JsonSchemaValue,
)
from .plugin._schema_validator import PluggableSchemaValidator, create_schema_validator

T = TypeVar('T')
R = TypeVar('R')
P = ParamSpec('P')
TypeAdapterT = TypeVar('TypeAdapterT', bound='TypeAdapter')


if TYPE_CHECKING:
    # should be `set[int] | set[str] | dict[int, IncEx] | dict[str, IncEx] | None`, but mypy can't cope
    IncEx = Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any]]


def _get_schema(type_: Any, config_wrapper: _config.ConfigWrapper, parent_depth: int) -> CoreSchema:
    """`BaseModel` uses its own `__module__` to find out where it was defined
    and then looks for symbols to resolve forward references in those globals.
    On the other hand this function can be called with arbitrary objects,
    including type aliases, where `__module__` (always `typing.py`) is not useful.
    So instead we look at the globals in our parent stack frame.

    This works for the case where this function is called in a module that
    has the target of forward references in its scope, but
    does not always work for more complex cases.

    For example, take the following:

    a.py
    ```python
    from typing import Dict, List

    IntList = List[int]
    OuterDict = Dict[str, 'IntList']
    ```

    b.py
    ```python test="skip"
    from a import OuterDict

    from pydantic import TypeAdapter

    IntList = int  # replaces the symbol the forward reference is looking for
    v = TypeAdapter(OuterDict)
    v({'x': 1})  # should fail but doesn't
    ```

    If `OuterDict` were a `BaseModel`, this would work because it would resolve
    the forward reference within the `a.py` namespace.
    But `TypeAdapter(OuterDict)` can't determine what module `OuterDict` came from.

    In other words, the assumption that _all_ forward references exist in the
    module we are being called from is not technically always true.
    Although most of the time it is and it works fine for recursive models and such,
    `BaseModel`'s behavior isn't perfect either and _can_ break in similar ways,
    so there is no right or wrong between the two.

    But at the very least this behavior is _subtly_ different from `BaseModel`'s.
    """
    local_ns = _typing_extra.parent_frame_namespace(parent_depth=parent_depth)
    global_ns = sys._getframe(max(parent_depth - 1, 1)).f_globals.copy()
    global_ns.update(local_ns or {})
    gen = _generate_schema.GenerateSchema(config_wrapper, types_namespace=global_ns, typevars_map={})
    schema = gen.generate_schema(type_)
    schema = gen.clean_schema(schema)
    return schema


def _getattr_no_parents(obj: Any, attribute: str) -> Any:
    """Returns the attribute value without attempting to look up attributes from parent types."""
    if hasattr(obj, '__dict__'):
        try:
            return obj.__dict__[attribute]
        except KeyError:
            pass

    slots = getattr(obj, '__slots__', None)
    if slots is not None and attribute in slots:
        return getattr(obj, attribute)
    else:
        raise AttributeError(attribute)


def _type_has_config(type_: Any) -> bool:
    """Returns whether the type has config."""
    type_ = _typing_extra.annotated_type(type_) or type_
    try:
        return issubclass(type_, BaseModel) or is_dataclass(type_) or is_typeddict(type_)
    except TypeError:
        # type is not a class
        return False


# This is keeping track of the frame depth for the TypeAdapter functions. This is required for _parent_depth used for
# ForwardRef resolution. We may enter the TypeAdapter schema building via different TypeAdapter functions. Hence, we
# need to keep track of the frame depth relative to the originally provided _parent_depth.
def _frame_depth(
    depth: int,
) -> Callable[[Callable[Concatenate[TypeAdapterT, P], R]], Callable[Concatenate[TypeAdapterT, P], R]]:
    def wrapper(func: Callable[Concatenate[TypeAdapterT, P], R]) -> Callable[Concatenate[TypeAdapterT, P], R]:
        @wraps(func)
        def wrapped(self: TypeAdapterT, *args: P.args, **kwargs: P.kwargs) -> R:
            with self._with_frame_depth(depth + 1):  # depth + 1 for the wrapper function
                return func(self, *args, **kwargs)

        return wrapped

    return wrapper


@final
class TypeAdapter(Generic[T]):
    """Usage docs: https://docs.pydantic.dev/2.8/concepts/type_adapter/

    Type adapters provide a flexible way to perform validation and serialization based on a Python type.

    A `TypeAdapter` instance exposes some of the functionality from `BaseModel` instance methods
    for types that do not have such methods (such as dataclasses, primitive types, and more).

    **Note:** `TypeAdapter` instances are not types, and cannot be used as type annotations for fields.

    **Note:** By default, `TypeAdapter` does not respect the
    [`defer_build=True`][pydantic.config.ConfigDict.defer_build] setting in the
    [`model_config`][pydantic.BaseModel.model_config] or in the `TypeAdapter` constructor `config`. You need to also
    explicitly set [`experimental_defer_build_mode=('model', 'type_adapter')`][pydantic.config.ConfigDict.experimental_defer_build_mode] of the
    config to defer the model validator and serializer construction. Thus, this feature is opt-in to ensure backwards
    compatibility.

    Attributes:
        core_schema: The core schema for the type.
        validator (SchemaValidator): The schema validator for the type.
        serializer: The schema serializer for the type.
    """

    @overload
    def __init__(
        self,
        type: type[T],
        *,
        config: ConfigDict | None = ...,
        _parent_depth: int = ...,
        module: str | None = ...,
    ) -> None: ...

    # This second overload is for unsupported special forms (such as Annotated, Union, etc.)
    # Currently there is no way to type this correctly
    # See https://github.com/python/typing/pull/1618
    @overload
    def __init__(
        self,
        type: Any,
        *,
        config: ConfigDict | None = ...,
        _parent_depth: int = ...,
        module: str | None = ...,
    ) -> None: ...

    def __init__(
        self,
        type: Any,
        *,
        config: ConfigDict | None = None,
        _parent_depth: int = 2,
        module: str | None = None,
    ) -> None:
        """Initializes the TypeAdapter object.

        Args:
            type: The type associated with the `TypeAdapter`.
            config: Configuration for the `TypeAdapter`, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].
            _parent_depth: depth at which to search the parent namespace to construct the local namespace.
            module: The module that passes to plugin if provided.

        !!! note
            You cannot use the `config` argument when instantiating a `TypeAdapter` if the type you're using has its own
            config that cannot be overridden (ex: `BaseModel`, `TypedDict`, and `dataclass`). A
            [`type-adapter-config-unused`](../errors/usage_errors.md#type-adapter-config-unused) error will be raised in this case.

        !!! note
            The `_parent_depth` argument is named with an underscore to suggest its private nature and discourage use.
            It may be deprecated in a minor version, so we only recommend using it if you're
            comfortable with potential change in behavior / support.

        ??? tip "Compatibility with `mypy`"
            Depending on the type used, `mypy` might raise an error when instantiating a `TypeAdapter`. As a workaround, you can explicitly
            annotate your variable:

            ```py
            from typing import Union

            from pydantic import TypeAdapter

            ta: TypeAdapter[Union[str, int]] = TypeAdapter(Union[str, int])  # type: ignore[arg-type]
            ```

        Returns:
            A type adapter configured for the specified `type`.
        """
        if _type_has_config(type) and config is not None:
            raise PydanticUserError(
                'Cannot use `config` when the type is a BaseModel, dataclass or TypedDict.'
                ' These types can have their own config and setting the config via the `config`'
                ' parameter to TypeAdapter will not override it, thus the `config` you passed to'
                ' TypeAdapter becomes meaningless, which is probably not what you want.',
                code='type-adapter-config-unused',
            )

        self._type = type
        self._config = config
        self._parent_depth = _parent_depth
        if module is None:
            f = sys._getframe(1)
            self._module_name = cast(str, f.f_globals.get('__name__', ''))
        else:
            self._module_name = module

        self._core_schema: CoreSchema | None = None
        self._validator: SchemaValidator | PluggableSchemaValidator | None = None
        self._serializer: SchemaSerializer | None = None

        if not self._defer_build():
            # Immediately initialize the core schema, validator and serializer
            with self._with_frame_depth(1):  # +1 frame depth for this __init__
                # Model itself may be using deferred building. For backward compatibility we don't rebuild model mocks
                # here as part of __init__ even though TypeAdapter itself is not using deferred building.
                self._init_core_attrs(rebuild_mocks=False)

    @contextmanager
    def _with_frame_depth(self, depth: int) -> Iterator[None]:
        self._parent_depth += depth
        try:
            yield
        finally:
            self._parent_depth -= depth

    @_frame_depth(1)
    def _init_core_attrs(self, rebuild_mocks: bool) -> None:
        try:
            self._core_schema = _getattr_no_parents(self._type, '__pydantic_core_schema__')
            self._validator = _getattr_no_parents(self._type, '__pydantic_validator__')
            self._serializer = _getattr_no_parents(self._type, '__pydantic_serializer__')
        except AttributeError:
            config_wrapper = _config.ConfigWrapper(self._config)
            core_config = config_wrapper.core_config(None)

            self._core_schema = _get_schema(self._type, config_wrapper, parent_depth=self._parent_depth)
            self._validator = create_schema_validator(
                schema=self._core_schema,
                schema_type=self._type,
                schema_type_module=self._module_name,
                schema_type_name=str(self._type),
                schema_kind='TypeAdapter',
                config=core_config,
                plugin_settings=config_wrapper.plugin_settings,
            )
            self._serializer = SchemaSerializer(self._core_schema, core_config)

        if rebuild_mocks and isinstance(self._core_schema, _mock_val_ser.MockCoreSchema):
            self._core_schema.rebuild()
            self._init_core_attrs(rebuild_mocks=False)
            assert not isinstance(self._core_schema, _mock_val_ser.MockCoreSchema)
            assert not isinstance(self._validator, _mock_val_ser.MockValSer)
            assert not isinstance(self._serializer, _mock_val_ser.MockValSer)

    @cached_property
    @_frame_depth(2)  # +2 for @cached_property and core_schema(self)
    def core_schema(self) -> CoreSchema:
        """The pydantic-core schema used to build the SchemaValidator and SchemaSerializer."""
        if self._core_schema is None or isinstance(self._core_schema, _mock_val_ser.MockCoreSchema):
            self._init_core_attrs(rebuild_mocks=True)  # Do not expose MockCoreSchema from public function
        assert self._core_schema is not None and not isinstance(self._core_schema, _mock_val_ser.MockCoreSchema)
        return self._core_schema

    @cached_property
    @_frame_depth(2)  # +2 for @cached_property + validator(self)
    def validator(self) -> SchemaValidator | PluggableSchemaValidator:
        """The pydantic-core SchemaValidator used to validate instances of the model."""
        if not isinstance(self._validator, (SchemaValidator, PluggableSchemaValidator)):
            self._init_core_attrs(rebuild_mocks=True)  # Do not expose MockValSer from public function
        assert isinstance(self._validator, (SchemaValidator, PluggableSchemaValidator))
        return self._validator

    @cached_property
    @_frame_depth(2)  # +2 for @cached_property + serializer(self)
    def serializer(self) -> SchemaSerializer:
        """The pydantic-core SchemaSerializer used to dump instances of the model."""
        if not isinstance(self._serializer, SchemaSerializer):
            self._init_core_attrs(rebuild_mocks=True)  # Do not expose MockValSer from public function
        assert isinstance(self._serializer, SchemaSerializer)
        return self._serializer

    def _defer_build(self) -> bool:
        config = self._config if self._config is not None else self._model_config()
        return self._is_defer_build_config(config) if config is not None else False

    def _model_config(self) -> ConfigDict | None:
        type_: Any = _typing_extra.annotated_type(self._type) or self._type  # Eg FastAPI heavily uses Annotated
        if _utils.lenient_issubclass(type_, BaseModel):
            return type_.model_config
        return getattr(type_, '__pydantic_config__', None)

    @staticmethod
    def _is_defer_build_config(config: ConfigDict) -> bool:
        # TODO reevaluate this logic when we have a better understanding of how defer_build should work with TypeAdapter
        # Should we drop the special experimental_defer_build_mode check?
        return config.get('defer_build', False) is True and 'type_adapter' in config.get(
            'experimental_defer_build_mode', tuple()
        )

    @_frame_depth(1)
    def validate_python(
        self,
        object: Any,
        /,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> T:
        """Validate a Python object against the model.

        Args:
            object: The Python object to validate against the model.
            strict: Whether to strictly check types.
            from_attributes: Whether to extract data from object attributes.
            context: Additional context to pass to the validator.

        !!! note
            When using `TypeAdapter` with a Pydantic `dataclass`, the use of the `from_attributes`
            argument is not supported.

        Returns:
            The validated object.
        """
        return self.validator.validate_python(object, strict=strict, from_attributes=from_attributes, context=context)

    @_frame_depth(1)
    def validate_json(
        self, data: str | bytes, /, *, strict: bool | None = None, context: dict[str, Any] | None = None
    ) -> T:
        """Usage docs: https://docs.pydantic.dev/2.8/concepts/json/#json-parsing

        Validate a JSON string or bytes against the model.

        Args:
            data: The JSON data to validate against the model.
            strict: Whether to strictly check types.
            context: Additional context to use during validation.

        Returns:
            The validated object.
        """
        return self.validator.validate_json(data, strict=strict, context=context)

    @_frame_depth(1)
    def validate_strings(self, obj: Any, /, *, strict: bool | None = None, context: dict[str, Any] | None = None) -> T:
        """Validate object contains string data against the model.

        Args:
            obj: The object contains string data to validate.
            strict: Whether to strictly check types.
            context: Additional context to use during validation.

        Returns:
            The validated object.
        """
        return self.validator.validate_strings(obj, strict=strict, context=context)

    @_frame_depth(1)
    def get_default_value(self, *, strict: bool | None = None, context: dict[str, Any] | None = None) -> Some[T] | None:
        """Get the default value for the wrapped type.

        Args:
            strict: Whether to strictly check types.
            context: Additional context to pass to the validator.

        Returns:
            The default value wrapped in a `Some` if there is one or None if not.
        """
        return self.validator.get_default_value(strict=strict, context=context)

    @_frame_depth(1)
    def dump_python(
        self,
        instance: T,
        /,
        *,
        mode: Literal['json', 'python'] = 'python',
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Dump an instance of the adapted type to a Python object.

        Args:
            instance: The Python object to serialize.
            mode: The output format.
            include: Fields to include in the output.
            exclude: Fields to exclude from the output.
            by_alias: Whether to use alias names for field names.
            exclude_unset: Whether to exclude unset fields.
            exclude_defaults: Whether to exclude fields with default values.
            exclude_none: Whether to exclude fields with None values.
            round_trip: Whether to output the serialized data in a way that is compatible with deserialization.
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
            context: Additional context to pass to the serializer.

        Returns:
            The serialized object.
        """
        return self.serializer.to_python(
            instance,
            mode=mode,
            by_alias=by_alias,
            include=include,
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
            context=context,
        )

    @_frame_depth(1)
    def dump_json(
        self,
        instance: T,
        /,
        *,
        indent: int | None = None,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
        context: dict[str, Any] | None = None,
    ) -> bytes:
        """Usage docs: https://docs.pydantic.dev/2.8/concepts/json/#json-serialization

        Serialize an instance of the adapted type to JSON.

        Args:
            instance: The instance to be serialized.
            indent: Number of spaces for JSON indentation.
            include: Fields to include.
            exclude: Fields to exclude.
            by_alias: Whether to use alias names for field names.
            exclude_unset: Whether to exclude unset fields.
            exclude_defaults: Whether to exclude fields with default values.
            exclude_none: Whether to exclude fields with a value of `None`.
            round_trip: Whether to serialize and deserialize the instance to ensure round-tripping.
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
            context: Additional context to pass to the serializer.

        Returns:
            The JSON representation of the given instance as bytes.
        """
        return self.serializer.to_json(
            instance,
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
            context=context,
        )

    @_frame_depth(1)
    def json_schema(
        self,
        *,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generate a JSON schema for the adapted type.

        Args:
            by_alias: Whether to use alias names for field names.
            ref_template: The format string used for generating $ref strings.
            schema_generator: The generator class used for creating the schema.
            mode: The mode to use for schema generation.

        Returns:
            The JSON schema for the model as a dictionary.
        """
        schema_generator_instance = schema_generator(by_alias=by_alias, ref_template=ref_template)
        return schema_generator_instance.generate(self.core_schema, mode=mode)

    @staticmethod
    def json_schemas(
        inputs: Iterable[tuple[JsonSchemaKeyT, JsonSchemaMode, TypeAdapter[Any]]],
        /,
        *,
        by_alias: bool = True,
        title: str | None = None,
        description: str | None = None,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
    ) -> tuple[dict[tuple[JsonSchemaKeyT, JsonSchemaMode], JsonSchemaValue], JsonSchemaValue]:
        """Generate a JSON schema including definitions from multiple type adapters.

        Args:
            inputs: Inputs to schema generation. The first two items will form the keys of the (first)
                output mapping; the type adapters will provide the core schemas that get converted into
                definitions in the output JSON schema.
            by_alias: Whether to use alias names.
            title: The title for the schema.
            description: The description for the schema.
            ref_template: The format string used for generating $ref strings.
            schema_generator: The generator class used for creating the schema.

        Returns:
            A tuple where:

                - The first element is a dictionary whose keys are tuples of JSON schema key type and JSON mode, and
                    whose values are the JSON schema corresponding to that pair of inputs. (These schemas may have
                    JsonRef references to definitions that are defined in the second returned element.)
                - The second element is a JSON schema containing all definitions referenced in the first returned
                    element, along with the optional title and description keys.

        """
        schema_generator_instance = schema_generator(by_alias=by_alias, ref_template=ref_template)

        inputs_ = []
        for key, mode, adapter in inputs:
            with adapter._with_frame_depth(1):  # +1 for json_schemas staticmethod
                inputs_.append((key, mode, adapter.core_schema))

        json_schemas_map, definitions = schema_generator_instance.generate_definitions(inputs_)

        json_schema: dict[str, Any] = {}
        if definitions:
            json_schema['$defs'] = definitions
        if title:
            json_schema['title'] = title
        if description:
            json_schema['description'] = description

        return json_schemas_map, json_schema
