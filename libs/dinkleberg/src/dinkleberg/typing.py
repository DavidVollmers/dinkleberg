import abc
import inspect
from functools import lru_cache
from inspect import Parameter, Signature
from typing import Callable, get_origin, get_type_hints

from dinkleberg_abc import Dependency


@lru_cache(maxsize=4096)
def get_signature(func: Callable) -> Signature:
    return inspect.signature(func)


@lru_cache(maxsize=4096)
def is_abstract(t: type) -> bool:
    return inspect.isabstract(t) or t is abc.ABC


@lru_cache(maxsize=4096)
def is_builtin_type(t: type) -> bool:
    origin = get_origin(t) or t
    return getattr(origin, '__module__', None) in ('builtins', 'typing', 'types')


@lru_cache(maxsize=4096)
def get_static_params(func: Callable) -> list[Parameter]:
    sig = get_signature(func)

    params = list(sig.parameters.values())

    if params and params[0].name in ('self', 'cls'):
        params = params[1:]

    return params


@lru_cache(maxsize=1024)
def get_methods_to_wrap(cls: type) -> tuple[str, ...]:
    cls = get_origin(cls) or cls

    methods_to_wrap = []

    for name in dir(cls):
        if name.startswith('_'):
            continue

        try:
            attr = getattr(cls, name)
            if not inspect.isfunction(attr):
                continue

            sig = get_signature(attr)
            for param in sig.parameters.values():
                if isinstance(param.default, Dependency):
                    methods_to_wrap.append(name)
                    break
        except (AttributeError, ValueError):
            continue

    return tuple(methods_to_wrap)


@lru_cache(maxsize=4096)
def get_cached_type_hints(obj: Callable) -> dict:
    # noinspection PyBroadException
    try:
        return get_type_hints(obj, include_extras=True)
    except Exception:
        return {}
