import inspect
from typing import get_origin, TYPE_CHECKING

from dinkleberg.dependency import _Dependency
from dinkleberg.typing import is_builtin_type, is_abstract, get_static_params, is_type_optional, get_methods_to_wrap, \
    get_signature

if TYPE_CHECKING:
    from dinkleberg import DependencyConfigurator


# noinspection PyProtectedMember
class DependencyInspector:
    def __init__(self, deps: 'DependencyConfigurator'):
        self._deps = deps

    def has_dependency(self, target_type: type, dependency_type: type) -> bool:
        visited = set()
        return self._check_dependency_tree(target_type, dependency_type, visited)

    def _check_dependency_tree(self, current_type: type, target_dep: type, visited: set[type]) -> bool:
        if current_type == target_dep:
            return True

        if current_type in visited:
            return False

        visited.add(current_type)

        direct_deps = self._get_direct_dependencies(current_type)

        for dep in direct_deps:
            if self._check_dependency_tree(dep, target_dep, visited):
                return True

        return False

    def _get_direct_dependencies(self, t: type) -> set[type]:
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

        deps = set()

        target_to_inspect = factory.__init__ if inspect.isclass(factory) else factory

        # noinspection PyBroadException
        try:
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
        except Exception:
            pass

        actual_type = origin if is_origin_class else t
        if inspect.isclass(actual_type):
            # noinspection PyBroadException
            try:
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
            except Exception:
                pass

        return deps
