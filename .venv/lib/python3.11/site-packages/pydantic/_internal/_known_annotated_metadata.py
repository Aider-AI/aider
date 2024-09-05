from __future__ import annotations

from collections import defaultdict
from copy import copy
from functools import lru_cache, partial
from typing import TYPE_CHECKING, Any, Callable, Iterable

from pydantic_core import CoreSchema, PydanticCustomError, to_jsonable_python
from pydantic_core import core_schema as cs

from ._fields import PydanticMetadata

if TYPE_CHECKING:
    from ..annotated_handlers import GetJsonSchemaHandler

STRICT = {'strict'}
FAIL_FAST = {'fail_fast'}
LENGTH_CONSTRAINTS = {'min_length', 'max_length'}
INEQUALITY = {'le', 'ge', 'lt', 'gt'}
NUMERIC_CONSTRAINTS = {'multiple_of', *INEQUALITY}
ALLOW_INF_NAN = {'allow_inf_nan'}

STR_CONSTRAINTS = {
    *LENGTH_CONSTRAINTS,
    *STRICT,
    'strip_whitespace',
    'to_lower',
    'to_upper',
    'pattern',
    'coerce_numbers_to_str',
}
BYTES_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}

LIST_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
TUPLE_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
SET_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
DICT_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}
GENERATOR_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}
SEQUENCE_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *FAIL_FAST}

FLOAT_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *ALLOW_INF_NAN, *STRICT}
DECIMAL_CONSTRAINTS = {'max_digits', 'decimal_places', *FLOAT_CONSTRAINTS}
INT_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *ALLOW_INF_NAN, *STRICT}
BOOL_CONSTRAINTS = STRICT
UUID_CONSTRAINTS = STRICT

DATE_TIME_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
TIMEDELTA_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
TIME_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
LAX_OR_STRICT_CONSTRAINTS = STRICT
ENUM_CONSTRAINTS = STRICT

UNION_CONSTRAINTS = {'union_mode'}
URL_CONSTRAINTS = {
    'max_length',
    'allowed_schemes',
    'host_required',
    'default_host',
    'default_port',
    'default_path',
}

TEXT_SCHEMA_TYPES = ('str', 'bytes', 'url', 'multi-host-url')
SEQUENCE_SCHEMA_TYPES = ('list', 'tuple', 'set', 'frozenset', 'generator', *TEXT_SCHEMA_TYPES)
NUMERIC_SCHEMA_TYPES = ('float', 'int', 'date', 'time', 'timedelta', 'datetime')

CONSTRAINTS_TO_ALLOWED_SCHEMAS: dict[str, set[str]] = defaultdict(set)

constraint_schema_pairings: list[tuple[set[str], tuple[str, ...]]] = [
    (STR_CONSTRAINTS, TEXT_SCHEMA_TYPES),
    (BYTES_CONSTRAINTS, ('bytes',)),
    (LIST_CONSTRAINTS, ('list',)),
    (TUPLE_CONSTRAINTS, ('tuple',)),
    (SET_CONSTRAINTS, ('set', 'frozenset')),
    (DICT_CONSTRAINTS, ('dict',)),
    (GENERATOR_CONSTRAINTS, ('generator',)),
    (FLOAT_CONSTRAINTS, ('float',)),
    (INT_CONSTRAINTS, ('int',)),
    (DATE_TIME_CONSTRAINTS, ('date', 'time', 'datetime')),
    (TIMEDELTA_CONSTRAINTS, ('timedelta',)),
    (TIME_CONSTRAINTS, ('time',)),
    # TODO: this is a bit redundant, we could probably avoid some of these
    (STRICT, (*TEXT_SCHEMA_TYPES, *SEQUENCE_SCHEMA_TYPES, *NUMERIC_SCHEMA_TYPES, 'typed-dict', 'model')),
    (UNION_CONSTRAINTS, ('union',)),
    (URL_CONSTRAINTS, ('url', 'multi-host-url')),
    (BOOL_CONSTRAINTS, ('bool',)),
    (UUID_CONSTRAINTS, ('uuid',)),
    (LAX_OR_STRICT_CONSTRAINTS, ('lax-or-strict',)),
    (ENUM_CONSTRAINTS, ('enum',)),
    (DECIMAL_CONSTRAINTS, ('decimal',)),
]

for constraints, schemas in constraint_schema_pairings:
    for c in constraints:
        CONSTRAINTS_TO_ALLOWED_SCHEMAS[c].update(schemas)


def add_js_update_schema(s: cs.CoreSchema, f: Callable[[], dict[str, Any]]) -> None:
    def update_js_schema(s: cs.CoreSchema, handler: GetJsonSchemaHandler) -> dict[str, Any]:
        js_schema = handler(s)
        js_schema.update(f())
        return js_schema

    if 'metadata' in s:
        metadata = s['metadata']
        if 'pydantic_js_functions' in s:
            metadata['pydantic_js_functions'].append(update_js_schema)
        else:
            metadata['pydantic_js_functions'] = [update_js_schema]
    else:
        s['metadata'] = {'pydantic_js_functions': [update_js_schema]}


def as_jsonable_value(v: Any) -> Any:
    if type(v) not in (int, str, float, bytes, bool, type(None)):
        return to_jsonable_python(v)
    return v


def expand_grouped_metadata(annotations: Iterable[Any]) -> Iterable[Any]:
    """Expand the annotations.

    Args:
        annotations: An iterable of annotations.

    Returns:
        An iterable of expanded annotations.

    Example:
        ```py
        from annotated_types import Ge, Len

        from pydantic._internal._known_annotated_metadata import expand_grouped_metadata

        print(list(expand_grouped_metadata([Ge(4), Len(5)])))
        #> [Ge(ge=4), MinLen(min_length=5)]
        ```
    """
    import annotated_types as at

    from pydantic.fields import FieldInfo  # circular import

    for annotation in annotations:
        if isinstance(annotation, at.GroupedMetadata):
            yield from annotation
        elif isinstance(annotation, FieldInfo):
            yield from annotation.metadata
            # this is a bit problematic in that it results in duplicate metadata
            # all of our "consumers" can handle it, but it is not ideal
            # we probably should split up FieldInfo into:
            # - annotated types metadata
            # - individual metadata known only to Pydantic
            annotation = copy(annotation)
            annotation.metadata = []
            yield annotation
        else:
            yield annotation


@lru_cache
def _get_at_to_constraint_map() -> dict[type, str]:
    """Return a mapping of annotated types to constraints.

    Normally, we would define a mapping like this in the module scope, but we can't do that
    because we don't permit module level imports of `annotated_types`, in an attempt to speed up
    the import time of `pydantic`. We still only want to have this dictionary defined in one place,
    so we use this function to cache the result.
    """
    import annotated_types as at

    return {
        at.Gt: 'gt',
        at.Ge: 'ge',
        at.Lt: 'lt',
        at.Le: 'le',
        at.MultipleOf: 'multiple_of',
        at.MinLen: 'min_length',
        at.MaxLen: 'max_length',
    }


def apply_known_metadata(annotation: Any, schema: CoreSchema) -> CoreSchema | None:  # noqa: C901
    """Apply `annotation` to `schema` if it is an annotation we know about (Gt, Le, etc.).
    Otherwise return `None`.

    This does not handle all known annotations. If / when it does, it can always
    return a CoreSchema and return the unmodified schema if the annotation should be ignored.

    Assumes that GroupedMetadata has already been expanded via `expand_grouped_metadata`.

    Args:
        annotation: The annotation.
        schema: The schema.

    Returns:
        An updated schema with annotation if it is an annotation we know about, `None` otherwise.

    Raises:
        PydanticCustomError: If `Predicate` fails.
    """
    import annotated_types as at

    from ._validators import forbid_inf_nan_check, get_constraint_validator

    schema = schema.copy()
    schema_update, other_metadata = collect_known_metadata([annotation])
    schema_type = schema['type']

    chain_schema_constraints: set[str] = {
        'pattern',
        'strip_whitespace',
        'to_lower',
        'to_upper',
        'coerce_numbers_to_str',
    }
    chain_schema_steps: list[CoreSchema] = []

    for constraint, value in schema_update.items():
        if constraint not in CONSTRAINTS_TO_ALLOWED_SCHEMAS:
            raise ValueError(f'Unknown constraint {constraint}')
        allowed_schemas = CONSTRAINTS_TO_ALLOWED_SCHEMAS[constraint]

        # if it becomes necessary to handle more than one constraint
        # in this recursive case with function-after or function-wrap, we should refactor
        # this is a bit challenging because we sometimes want to apply constraints to the inner schema,
        # whereas other times we want to wrap the existing schema with a new one that enforces a new constraint.
        if schema_type in {'function-before', 'function-wrap', 'function-after'} and constraint == 'strict':
            schema['schema'] = apply_known_metadata(annotation, schema['schema'])  # type: ignore  # schema is function-after schema
            return schema

        if schema_type in allowed_schemas:
            if constraint == 'union_mode' and schema_type == 'union':
                schema['mode'] = value  # type: ignore  # schema is UnionSchema
            else:
                schema[constraint] = value
            continue

        if constraint in chain_schema_constraints:
            chain_schema_steps.append(cs.str_schema(**{constraint: value}))
        elif constraint in {*NUMERIC_CONSTRAINTS, *LENGTH_CONSTRAINTS}:
            if constraint in NUMERIC_CONSTRAINTS:
                json_schema_constraint = constraint
            elif constraint in LENGTH_CONSTRAINTS:
                inner_schema = schema
                while inner_schema['type'] in {'function-before', 'function-wrap', 'function-after'}:
                    inner_schema = inner_schema['schema']  # type: ignore
                inner_schema_type = inner_schema['type']
                if inner_schema_type == 'list' or (
                    inner_schema_type == 'json-or-python' and inner_schema['json_schema']['type'] == 'list'  # type: ignore
                ):
                    json_schema_constraint = 'minItems' if constraint == 'min_length' else 'maxItems'
                else:
                    json_schema_constraint = 'minLength' if constraint == 'min_length' else 'maxLength'

            schema = cs.no_info_after_validator_function(
                partial(get_constraint_validator(constraint), **{constraint: value}), schema
            )
            add_js_update_schema(schema, lambda: {json_schema_constraint: as_jsonable_value(value)})
        elif constraint == 'allow_inf_nan' and value is False:
            schema = cs.no_info_after_validator_function(
                forbid_inf_nan_check,
                schema,
            )
        else:
            raise RuntimeError(f'Unable to apply constraint {constraint} to schema {schema_type}')

    for annotation in other_metadata:
        if (annotation_type := type(annotation)) in (at_to_constraint_map := _get_at_to_constraint_map()):
            constraint = at_to_constraint_map[annotation_type]
            schema = cs.no_info_after_validator_function(
                partial(get_constraint_validator(constraint), {constraint: getattr(annotation, constraint)}), schema
            )
            continue
        elif isinstance(annotation, at.Predicate):
            predicate_name = f'{annotation.func.__qualname__} ' if hasattr(annotation.func, '__qualname__') else ''

            def val_func(v: Any) -> Any:
                # annotation.func may also raise an exception, let it pass through
                if not annotation.func(v):
                    raise PydanticCustomError(
                        'predicate_failed',
                        f'Predicate {predicate_name}failed',  # type: ignore
                    )
                return v

            schema = cs.no_info_after_validator_function(val_func, schema)
        else:
            # ignore any other unknown metadata
            return None

    if chain_schema_steps:
        chain_schema_steps = [schema] + chain_schema_steps
        return cs.chain_schema(chain_schema_steps)

    return schema


def collect_known_metadata(annotations: Iterable[Any]) -> tuple[dict[str, Any], list[Any]]:
    """Split `annotations` into known metadata and unknown annotations.

    Args:
        annotations: An iterable of annotations.

    Returns:
        A tuple contains a dict of known metadata and a list of unknown annotations.

    Example:
        ```py
        from annotated_types import Gt, Len

        from pydantic._internal._known_annotated_metadata import collect_known_metadata

        print(collect_known_metadata([Gt(1), Len(42), ...]))
        #> ({'gt': 1, 'min_length': 42}, [Ellipsis])
        ```
    """
    annotations = expand_grouped_metadata(annotations)

    res: dict[str, Any] = {}
    remaining: list[Any] = []

    for annotation in annotations:
        # isinstance(annotation, PydanticMetadata) also covers ._fields:_PydanticGeneralMetadata
        if isinstance(annotation, PydanticMetadata):
            res.update(annotation.__dict__)
        # we don't use dataclasses.asdict because that recursively calls asdict on the field values
        elif (annotation_type := type(annotation)) in (at_to_constraint_map := _get_at_to_constraint_map()):
            constraint = at_to_constraint_map[annotation_type]
            res[constraint] = getattr(annotation, constraint)
        elif isinstance(annotation, type) and issubclass(annotation, PydanticMetadata):
            # also support PydanticMetadata classes being used without initialisation,
            # e.g. `Annotated[int, Strict]` as well as `Annotated[int, Strict()]`
            res.update({k: v for k, v in vars(annotation).items() if not k.startswith('_')})
        else:
            remaining.append(annotation)
    # Nones can sneak in but pydantic-core will reject them
    # it'd be nice to clean things up so we don't put in None (we probably don't _need_ to, it was just easier)
    # but this is simple enough to kick that can down the road
    res = {k: v for k, v in res.items() if v is not None}
    return res, remaining


def check_metadata(metadata: dict[str, Any], allowed: Iterable[str], source_type: Any) -> None:
    """A small utility function to validate that the given metadata can be applied to the target.
    More than saving lines of code, this gives us a consistent error message for all of our internal implementations.

    Args:
        metadata: A dict of metadata.
        allowed: An iterable of allowed metadata.
        source_type: The source type.

    Raises:
        TypeError: If there is metadatas that can't be applied on source type.
    """
    unknown = metadata.keys() - set(allowed)
    if unknown:
        raise TypeError(
            f'The following constraints cannot be applied to {source_type!r}: {", ".join([f"{k!r}" for k in unknown])}'
        )
