import asyncio
import inspect
import logging
from functools import wraps
from inspect import Signature
from types import MappingProxyType
from typing import AsyncGenerator, Callable, overload, get_type_hints, Mapping, get_origin, get_args

from dinkleberg_abc import DependencyScope, Dependency
from .descriptor import Descriptor, Lifetime
from .typing import get_static_params, is_builtin_type, is_abstract, get_signature, get_methods_to_wrap, \
    get_cached_type_hints

logger = logging.getLogger(__name__)


# noinspection PyShadowingBuiltins
class DependencyConfigurator(DependencyScope):
    def __init__(self, parent: 'DependencyConfigurator' = None) -> None:
        super().__init__()
        self._parent = parent
        self._descriptors: dict[type, Descriptor] = {}
        self._singleton_instances = {}
        self._scoped_instances = {}
        self._configurators: dict[type, list[Callable[[object], object | None]]] = {}
        self._active_generators = []
        self._scopes = []
        self._closed = False

    def configure[T](self, t: type[T], configurator: Callable[[T], T | None]) -> None:
        self._raise_if_closed()
        if t not in self._configurators:
            self._configurators[t] = []
        self._configurators[t].append(configurator)

    # TODO race condition prevention (async.Lock)
    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        exceptions = []

        for generator in reversed(self._active_generators):
            try:
                await generator.__anext__()
                raise RuntimeError('Generator did not stop after yielding a single value.')
            except StopAsyncIteration:
                pass
            except Exception as e:
                exceptions.append(e)

        for scope in self._scopes:
            try:
                await scope.close()
            except Exception as e:
                exceptions.append(e)

        self._singleton_instances.clear()
        self._active_generators.clear()
        self._scoped_instances.clear()
        self._configurators.clear()
        self._descriptors.clear()
        self._scopes.clear()

        if exceptions:
            raise ExceptionGroup('Errors occurred during closing DependencyConfigurator', exceptions)

    def _add(self, lifetime: Lifetime, *, t: type = None, i: type = None,
             generator: Callable[..., AsyncGenerator] = None, callable: Callable = None, override: bool = False):
        if t is None and i is None and generator is None and callable is None:
            raise ValueError(
                'Invalid dependency registration. At least one of t, i, generator, or callable must be provided.')

        if lifetime == 'singleton' and self._parent is not None:
            raise RuntimeError(
                'Singleton dependencies, which are not instances, '
                'can only be registered in the root DependencyConfigurator.')

        if i is not None:
            if is_builtin_type(i):
                raise TypeError(f'Cannot use built-in type {i} as implementation.')

            if get_origin(i) is not None:
                raise TypeError(f'Cannot use generic type {i} as implementation.')

            if is_abstract(i):
                raise TypeError(f'Cannot use abstract class {i} as implementation.')

        if t is None:
            if i is not None:
                t = i
            else:
                t = self._infer_type(generator=generator, callable=callable)
        elif generator is None and callable is None and i is None:
            if is_builtin_type(t):
                raise TypeError(
                    f'Cannot register built-in type {t} without explicit implementation, generator or callable.')

            if get_origin(t) is not None:
                raise TypeError(
                    f'Cannot register generic type {t} without explicit implementation, generator or callable.')

            if is_abstract(t):
                raise TypeError(
                    f'Cannot register abstract class {t} without explicit implementation, generator or callable.')

        if t in self._descriptors and not override:
            raise ValueError(f'Type {t} is already registered.')

        self._descriptors[t] = Descriptor(implementation=i, generator=generator, callable=callable, lifetime=lifetime)

    @staticmethod
    def _infer_type(*, generator: Callable[..., AsyncGenerator], callable: Callable) -> type:
        # noinspection PyBroadException
        try:
            hints = get_type_hints(generator or callable)
            return_hint = hints.get('return')

            if not return_hint:
                pass

            origin = get_origin(return_hint)
            if origin is AsyncGenerator:
                return return_hint.__args__[0]

            return return_hint
        except Exception:
            pass
        raise TypeError('Could not infer type from generator. Please provide the type explicitly.')

    def _raise_if_closed(self):
        if self._closed:
            raise RuntimeError('DependencyScope is already closed.')

    def scope(self) -> 'DependencyConfigurator':
        self._raise_if_closed()
        scope = DependencyConfigurator(self)
        scope._descriptors = self._descriptors.copy()
        scope._configurators = self._configurators.copy()
        self._scopes.append(scope)
        return scope

    def _lookup_singleton(self, t: type):
        if t in self._singleton_instances:
            return self._configure_instance(t, self._singleton_instances[t])
        if self._parent:
            return self._parent._lookup_singleton(t)
        return None

    # TODO circular dependency detection
    # TODO singleton race condition prevention (async.Lock)
    async def resolve[T](self, t: type[T] | Callable, **kwargs) -> T:
        self._raise_if_closed()

        origin = get_origin(t)
        is_new_type = hasattr(t, '__supertype__')
        if not inspect.isclass(t) and origin is None and not is_new_type:
            if not inspect.isfunction(t):
                raise TypeError(f'Cannot resolve type {t}. Only classes and functions are supported.')

            return self._wrap_func(t)

        if t == DependencyScope or t == DependencyConfigurator:
            return self._configure_instance(t, self)

        singleton = self._lookup_singleton(t)
        if singleton is not None:
            return singleton
        if t in self._scoped_instances:
            return self._configure_instance(t, self._scoped_instances[t])

        descriptor = self._descriptors.get(t)
        is_origin_class = inspect.isclass(origin)
        if descriptor is None and is_origin_class:
            # noinspection PyTypeChecker
            descriptor = self._descriptors.get(origin)

        if descriptor is None or descriptor['generator'] is None and descriptor['callable'] is None:

            generic_map = None
            if descriptor is None:
                if is_builtin_type(t):
                    raise TypeError(f'Cannot resolve built-in type {t} without explicit registration.')

                if origin is not None:
                    raise TypeError(f'Cannot resolve generic type {t} without explicit registration.')

                if is_abstract(t):
                    raise TypeError(f'Cannot resolve abstract class {t} without explicit registration.')

                factory = t
            elif is_origin_class:
                factory = descriptor['implementation'] or origin

                type_params = getattr(origin, '__type_params__', getattr(origin, '__parameters__', None))
                t_args = get_args(t)
                if type_params and t_args:
                    generic_map = dict(zip(type_params, t_args))
            else:
                factory = descriptor['implementation'] or t

            is_generator = False
            lifetime = descriptor['lifetime'] if descriptor else 'transient'
            factory_kwargs = await self._resolve_factory_kwargs(factory.__init__, kwargs, generic_map)
        else:
            lifetime = descriptor['lifetime']
            if lifetime == 'singleton' and self._parent:
                # we need to resolve singleton from the root scope
                return await self._parent.resolve(t, **kwargs)

            is_generator = descriptor['generator'] is not None
            factory = descriptor['generator'] or descriptor['callable']

            generic_map = None
            if is_origin_class:
                generic_map = self._infer_return_generics(factory, t)

            factory_kwargs = await self._resolve_factory_kwargs(factory, kwargs, generic_map)

        if is_generator:
            generator = factory(**factory_kwargs)
            try:
                instance = await generator.__anext__()
            except StopAsyncIteration:
                raise RuntimeError(f'Generator {t} did not yield any value.')

            self._active_generators.append(generator)
        elif asyncio.iscoroutinefunction(factory):
            instance = await factory(**factory_kwargs)
        else:
            instance = factory(**factory_kwargs)

        if isinstance(instance, AsyncGenerator):
            try:
                if is_generator:
                    raise RuntimeError(f'Generator {t} yielded another generator. Nested generators are not supported.')
                else:
                    raise RuntimeError(
                        f'Callable {t} returned a generator. '
                        f'This is most likely due to an invalid dependency registration.')
            finally:
                await instance.aclose()

        configured_instance = self._configure_instance(t, instance)

        wrapped_instance = self._wrap_instance(t, configured_instance)

        if lifetime == 'singleton':
            self._singleton_instances[t] = wrapped_instance
        elif lifetime == 'scoped':
            self._scoped_instances[t] = wrapped_instance

        return wrapped_instance

    @staticmethod
    def _infer_return_generics(factory: Callable, requested_type: type) -> dict:
        hints = get_cached_type_hints(factory)
        return_hint = hints.get('return')

        if not return_hint:
            return {}

        req_origin = get_origin(requested_type) or requested_type
        ret_origin = get_origin(return_hint) or return_hint

        if req_origin != ret_origin:
            return {}

        req_args = get_args(requested_type)
        ret_args = get_args(return_hint)

        return dict(zip(ret_args, req_args))

    async def _batch_resolve(self, requests: list[tuple[str, type, dict]]) -> dict:
        results = {}
        tasks = []
        task_names = []

        for name, t, kwargs in requests:
            singleton = self._lookup_singleton(t)
            if singleton is not None:
                results[name] = singleton
                continue

            task_names.append(name)
            tasks.append(self.resolve(t, **kwargs))

        if tasks:
            resolved_values = await asyncio.gather(*tasks)
            results.update(zip(task_names, resolved_values))

        return results

    async def _resolve_factory_kwargs(self, factory: Callable, kwargs: dict, generic_map: dict = None) -> dict:
        params = get_static_params(factory)

        final_kwargs = {}
        requests = []

        for param in params:
            name = param.name
            ann = param.annotation

            if name in kwargs:
                final_kwargs[name] = kwargs[name]
                continue

            if ann is inspect.Parameter.empty:
                continue

            resolve_type = ann
            if generic_map:
                if get_origin(ann) is type:
                    arg = get_args(ann)[0]
                    if arg in generic_map:
                        final_kwargs[name] = generic_map[arg]
                        continue

                if ann in generic_map:
                    resolve_type = generic_map[ann]

            if is_builtin_type(resolve_type):
                continue

            requests.append((name, resolve_type, {}))

        resolved_deps = await self._batch_resolve(requests)
        final_kwargs.update(resolved_deps)

        return final_kwargs

    async def _resolve_kwargs(self, signature: Signature, name: str, args: tuple, kwargs: dict,
                              dep_params: Mapping[str, inspect.Parameter]) -> dict:
        bound_args = signature.bind_partial(*args, **kwargs)
        actual_kwargs = kwargs.copy()

        requests = []

        for p_name, p_param in dep_params.items():
            if p_name in bound_args.arguments:
                continue

            ann = p_param.annotation
            if ann is inspect.Parameter.empty:
                raise TypeError(f'Parameter "{p_name}" in {name} ...')

            # noinspection PyProtectedMember
            dep_kwargs = p_param.default._kwargs
            merged_kwargs = {**dep_kwargs, **kwargs}

            requests.append((p_name, ann, merged_kwargs))

        resolved_deps = await self._batch_resolve(requests)
        actual_kwargs.update(resolved_deps)

        return actual_kwargs

    def _wrap_func(self, func: Callable):
        signature = get_signature(func)

        dep_params = MappingProxyType({
            param_name: param
            for param_name, param in signature.parameters.items()
            if isinstance(param.default, Dependency)
        })

        if not dep_params:
            return func

        if not asyncio.iscoroutinefunction(func):
            raise NotImplementedError('Synchronous functions with Dependency() defaults are not supported.')

        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            new_kwargs = await self._resolve_kwargs(signature, func.__name__, args, kwargs, dep_params)
            return await func(*args, **new_kwargs)

        return wrapped_func

    def _configure_instance(self, t: type, instance: object) -> object:
        if t not in self._configurators:
            return instance

        for configurator in self._configurators[t]:
            result = configurator(instance)
            if result is not None:
                instance = result

        return instance

    # TODO handle __slots__
    def _wrap_instance(self, t: type, instance: object) -> object:
        if hasattr(instance, '__dinkleberg__') or is_builtin_type(t):
            return instance

        for name in get_methods_to_wrap(t):
            instance_method = getattr(instance, name)
            wrapped = self._wrap_func(instance_method)
            if wrapped is not instance_method:
                setattr(instance, name, wrapped)

        try:
            setattr(instance, '__dinkleberg__', True)
        except (AttributeError, TypeError):
            # Some objects (like those with __slots__) might not allow new attributes
            pass

        return instance

    @overload
    def add_singleton[I](self, *, instance: I, override: bool = False):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], instance: I, override: bool = False):
        ...

    @overload
    def add_singleton[T](self, *, t: type[T], override: bool = False):
        ...

    @overload
    def add_singleton[I](self, *, i: type[I], override: bool = False):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], i: type[I], override: bool = False):
        ...

    @overload
    def add_singleton[I](self, *, callable: Callable[..., I], override: bool = False):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], callable: Callable[..., I], override: bool = False):
        ...

    @overload
    def add_singleton[I](self, *, generator: Callable[..., AsyncGenerator[I, None]], override: bool = False):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], generator: Callable[..., AsyncGenerator[I, None]],
                            override: bool = False):
        ...

    def add_singleton[T, I](self, *, t: type[T] = None, i: type[I] = None,
                            generator: Callable[..., AsyncGenerator[I, None]] = None,
                            callable: Callable[..., I] = None, instance: I = None, override: bool = False):
        self._raise_if_closed()

        if instance is None:
            self._add('singleton', t=t, i=i, generator=generator, callable=callable, override=override)
            return
        elif t is None:
            t = type(instance)

        if t in self._descriptors and not override:
            raise ValueError(f'Type {t} is already registered with a descriptor. Cannot register singleton instance.')

        if t in self._singleton_instances and not override:
            raise ValueError(f'Type {t} already has a singleton instance registered.')

        configured_instance = self._configure_instance(t, instance)

        wrapped_instance = self._wrap_instance(t, configured_instance)

        self._singleton_instances[t] = wrapped_instance

        if t in self._descriptors:
            del self._descriptors[t]

    @overload
    def add_scoped[T](self, *, t: type[T], override: bool = False):
        ...

    @overload
    def add_scoped[I](self, *, i: type[I], override: bool = False):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], i: type[I], override: bool = False):
        ...

    @overload
    def add_scoped[I](self, *, callable: Callable[..., I], override: bool = False):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], callable: Callable[..., I], override: bool = False):
        ...

    @overload
    def add_scoped[I](self, *, generator: Callable[..., AsyncGenerator[I, None]], override: bool = False):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], generator: Callable[..., AsyncGenerator[I, None]],
                         override: bool = False):
        ...

    def add_scoped[T, I](self, *, t: type[T] = None, i: type[I] = None,
                         generator: Callable[..., AsyncGenerator[I, None]] = None, callable: Callable[..., I] = None,
                         override: bool = False):
        self._raise_if_closed()
        self._add('scoped', t=t, i=i, generator=generator, callable=callable, override=override)

    @overload
    def add_transient[T](self, *, t: type[T], override: bool = False):
        ...

    @overload
    def add_transient[I](self, *, i: type[I], override: bool = False):
        ...

    @overload
    def add_transient[T, I](self, *, t: type[T], i: type[I], override: bool = False):
        ...

    @overload
    def add_transient[I](self, *, callable: Callable[..., I], override: bool = False):
        ...

    @overload
    def add_transient[T, I](self, *, t: type[T], callable: Callable[..., I], override: bool = False):
        ...

    def add_transient[T, I](self, *, t: type[T] = None, i: type[I] = None, callable: Callable[..., I] = None,
                            override: bool = False):
        self._raise_if_closed()
        self._add('transient', i=i, t=t, callable=callable, override=override)
