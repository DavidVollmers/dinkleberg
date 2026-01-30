import inspect
from inspect import Parameter, signature
from typing import Callable


def get_static_params(func: Callable) -> list[Parameter]:
    sig = signature(func)

    params = list(sig.parameters.values())

    if params and params[0].name in ('self', 'cls'):
        params = params[1:]

    return params


def get_public_methods(obj: object) -> list[tuple[str, Callable]]:
    methods = []

    for name in dir(obj.__class__):
        attr = getattr(obj.__class__, name)

        if inspect.isroutine(attr) and not isinstance(attr, property) and not name.startswith('_'):
            methods.append((name, attr))

    return methods
