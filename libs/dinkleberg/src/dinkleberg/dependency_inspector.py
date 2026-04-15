import inspect
from typing import get_origin, TYPE_CHECKING, Callable

from dinkleberg.dependency import _Dependency
from dinkleberg.typing import is_builtin_type, is_abstract, get_static_params, is_type_optional, get_methods_to_wrap, \
    get_signature

if TYPE_CHECKING:
    from dinkleberg import DependencyConfigurator


# noinspection PyProtectedMember
class DependencyInspector:
    def __init__(self, deps: 'DependencyConfigurator'):
        self._deps = deps

    def has_dependency(self, target_type: type | Callable, dependency_type: type) -> bool:
        visited = set()
        return self._check_dependency_tree(target_type, dependency_type, visited)

    def _check_dependency_tree(self, current: type | Callable, target_dep: type, visited: set) -> bool:
        if current == target_dep:
            return True

        if current in visited:
            return False

        visited.add(current)

        direct_deps = self._get_direct_dependencies(current)

        for dep in direct_deps:
            if self._check_dependency_tree(dep, target_dep, visited):
                return True

        return False

    def _get_direct_dependencies(self, t: type | Callable) -> set[type]:
        deps = set()

        if inspect.isroutine(t):
            sig = get_signature(t)
            for param in sig.parameters.values():
                if isinstance(param.default, _Dependency):
                    ann = param.annotation
                    if ann is inspect.Parameter.empty and param.default._t is not None:
                        ann = param.default._t

                    if ann is not inspect.Parameter.empty:
                        _, resolve_type = is_type_optional(ann)
                        if isinstance(resolve_type, str):
                            resolve_type = self._resolve_string_reference(resolve_type) or resolve_type

                        deps.add(resolve_type)
            return deps

        origin = get_origin(t)
        descriptor = self._deps._descriptors.get(t)
        is_origin_class = inspect.isclass(origin)

        if descriptor is None and is_origin_class:
            descriptor = self._deps._descriptors.get(origin)

        factory = None
        if descriptor:
            if descriptor['implementation'] is not None:
                return {descriptor['implementation']}
            factory = descriptor['generator'] or descriptor['callable']

        if factory is None:
            if is_builtin_type(t) or is_abstract(t):
                return set()
            factory = origin if is_origin_class else t

        target_to_inspect = factory.__init__ if inspect.isclass(factory) else factory

        params = get_static_params(target_to_inspect)
        for param in params:
            if inspect.isclass(factory) and param.name == 'self':
                continue

            if param.annotation is not inspect.Parameter.empty:
                _, resolve_type = is_type_optional(param.annotation)

                if isinstance(resolve_type, str):
                    for registered_type in self._deps._descriptors.keys():
                        if getattr(registered_type, '__name__', '') == resolve_type:
                            resolve_type = registered_type
                            break

                deps.add(resolve_type)

        actual_type = origin if is_origin_class else t
        if inspect.isclass(actual_type):
            for name in get_methods_to_wrap(actual_type):
                method = getattr(actual_type, name)
                sig = get_signature(method)

                for param in sig.parameters.values():
                    if isinstance(param.default, _Dependency):
                        ann = param.annotation
                        if ann is inspect.Parameter.empty and param.default._t is not None:
                            ann = param.default._t

                        if ann is not inspect.Parameter.empty:
                            _, resolve_type = is_type_optional(ann)

                            if isinstance(resolve_type, str):
                                for registered_type in self._deps._descriptors.keys():
                                    if getattr(registered_type, '__name__', '') == resolve_type:
                                        resolve_type = registered_type
                                        break

                            deps.add(resolve_type)

        return deps

    def _resolve_string_reference(self, type_name: str) -> type | None:
        for registered_type in self._deps._descriptors.keys():
            if getattr(registered_type, '__name__', '') == type_name:
                return registered_type
        return None
