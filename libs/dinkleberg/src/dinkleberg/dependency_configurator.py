import asyncio
import inspect
import logging
from inspect import Signature
from types import MappingProxyType
from typing import AsyncGenerator, Callable, overload, get_type_hints, Mapping, get_origin

from dinkleberg_abc import DependencyScope, Dependency
from .descriptor import Descriptor, Lifetime
from .typing import get_static_params, get_public_methods, is_builtin_type, is_abstract

logger = logging.getLogger(__name__)


# noinspection PyShadowingBuiltins
class DependencyConfigurator(DependencyScope):
    def __init__(self, parent: 'DependencyConfigurator' = None) -> None:
        super().__init__()
        self._parent = parent
        self._descriptors: dict[type, Descriptor] = {}
        self._singleton_instances = {}
        self._scoped_instances = {}
        self._active_generators = []
        self._scopes = []
        self._closed = False

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        exceptions = []

        # TODO close generators in reverse order of creation (LIFO)
        for generator in self._active_generators:
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
        self._descriptors.clear()
        self._scopes.clear()

        if exceptions:
            raise ExceptionGroup('Errors occurred during closing DependencyConfigurator', exceptions)

    def _add(self, lifetime: Lifetime, *, t: type = None, i: type = None,
             generator: Callable[..., AsyncGenerator] = None, callable: Callable = None):
        if t is None and i is None and generator is None and callable is None:
            raise ValueError(
                'Invalid dependency registration. At least one of t, i, generator, or callable must be provided.')
        if i is not None:
            if is_builtin_type(i):
                raise ValueError(f'Cannot use built-in type {i} as implementation.')

            if get_origin(i) is not None:
                raise ValueError(f'Cannot use generic type {i} as implementation.')

            if is_abstract(i):
                raise ValueError(f'Cannot use abstract class {i} as implementation.')
        if t is None:
            if i is not None:
                t = i
            else:
                t = self._infer_type(generator=generator, callable=callable)
        elif generator is None and callable is None:
            if is_builtin_type(t):
                raise ValueError(
                    f'Cannot register built-in type {t} without explicit implementation, generator or callable.')

            if get_origin(t) is not None:
                raise ValueError(
                    f'Cannot register generic type {t} without explicit implementation, generator or callable.')

            if is_abstract(t):
                raise ValueError(
                    f'Cannot register abstract class {t} without explicit implementation, generator or callable.')
        self._descriptors[t] = Descriptor(implementation=i, generator=generator, callable=callable, lifetime=lifetime)

    @staticmethod
    def _infer_type(*, generator: Callable[..., AsyncGenerator], callable: Callable) -> type:
        # noinspection PyBroadException
        try:
            hints = get_type_hints(generator or callable)
            return_hint = hints.get('return')

            if not return_hint:
                pass

            # This looks for the generic arguments of the return type
            # e.g., if hint is AsyncGenerator[User, None], it extracts User
            if hasattr(return_hint, '__args__'):
                return return_hint.__args__[0]
            return return_hint
        except Exception:
            pass
        raise ValueError('Could not infer type from generator. Please provide the type explicitly.')

    def _raise_if_closed(self):
        if self._closed:
            raise RuntimeError('DependencyConfigurator is already closed.')

    def scope(self) -> 'DependencyConfigurator':
        self._raise_if_closed()
        scope = DependencyConfigurator(self)
        scope._descriptors = self._descriptors.copy()
        self._scopes.append(scope)
        return scope

    def _lookup_singleton(self, t: type):
        if t in self._singleton_instances:
            return self._singleton_instances[t]
        if self._parent:
            return self._parent._lookup_singleton(t)
        return None

    # TODO circular dependency detection
    # TODO singleton race condition prevention (async.Lock)
    async def resolve[T](self, t: type[T], **kwargs) -> T:
        self._raise_if_closed()

        if t == DependencyScope:
            return self

        singleton = self._lookup_singleton(t)
        if singleton is not None:
            return singleton
        if t in self._scoped_instances:
            return self._scoped_instances[t]

        descriptor = self._descriptors.get(t)
        if descriptor is None or descriptor['implementation'] is not None:
            if descriptor is None:
                if is_builtin_type(t):
                    raise ValueError(f'Cannot resolve built-in type {t} without explicit registration.')

                if get_origin(t) is not None:
                    raise ValueError(f'Cannot resolve generic type {t} without explicit registration.')

                if is_abstract(t):
                    raise ValueError(f'Cannot resolve abstract class {t} without explicit registration.')

                factory = t
            else:
                factory = descriptor['implementation'] or t

            is_generator = False
            lifetime = descriptor['lifetime'] if descriptor else 'transient'
            deps = await self._resolve_deps(factory.__init__)
        else:
            descriptor = self._descriptors[t]
            lifetime = descriptor['lifetime']
            if lifetime == 'singleton' and self._parent:
                # we need to resolve singleton from the root scope
                return await self._parent.resolve(t, **kwargs)

            is_generator = descriptor['generator'] is not None
            factory = descriptor['generator'] or descriptor['callable']
            deps = await self._resolve_deps(factory)

        if is_generator:
            generator = factory(**deps, **kwargs)
            try:
                instance = await generator.__anext__()
            except StopAsyncIteration:
                raise RuntimeError(f'Generator {t} did not yield any value.')

            self._active_generators.append(generator)
        elif asyncio.iscoroutinefunction(factory):
            instance = await factory(**deps, **kwargs)
        else:
            instance = factory(**deps, **kwargs)

        if isinstance(instance, AsyncGenerator):
            try:
                if is_generator:
                    raise RuntimeError(f'Generator {t} yielded another generator. Nested generators are not supported.')
                else:
                    raise RuntimeError(
                        f'Callable {t} returned a generator. This is most likely due to an invalid dependency registration.')
            finally:
                await instance.aclose()

        self._wrap_instance(instance)

        if lifetime == 'singleton':
            self._singleton_instances[t] = instance
        elif lifetime == 'scoped':
            self._scoped_instances[t] = instance

        return instance

    async def _resolve_deps(self, func: Callable) -> dict:
        params = get_static_params(func)
        tasks = []
        names = []

        for param in params:
            if not param.annotation or param.annotation is inspect.Parameter.empty:
                continue

            if is_builtin_type(param.annotation):
                continue

            # TODO handle more complex cases (e.g., Union, Optional, etc.)
            names.append(param.name)
            tasks.append(self.resolve(param.annotation))

        results = await asyncio.gather(*tasks)
        return dict(zip(names, results))

    async def _resolve_kwargs(self, signature: Signature, name: str, args: tuple, kwargs: dict,
                              dep_params: Mapping[str, inspect.Parameter]) -> dict:
        bound_args = signature.bind_partial(*args, **kwargs)
        actual_kwargs = kwargs.copy()

        params_to_resolve = []
        for p_name, p_obj in dep_params.items():
            if p_name not in bound_args.arguments:
                if p_obj.annotation is inspect.Parameter.empty:
                    raise TypeError(f'Parameter "{p_name}" in {name} is marked as a Dependency but lacks a type hint.')
                params_to_resolve.append((p_name, p_obj.annotation))

        if not params_to_resolve:
            return actual_kwargs

        names, types = zip(*params_to_resolve)
        resolved_values = await asyncio.gather(*(self.resolve(t, **kwargs) for t in types))

        actual_kwargs.update(dict(zip(names, resolved_values)))

        return actual_kwargs

    # TODO handle __slots__
    def _wrap_instance(self, instance):
        if getattr(instance, '__dinkleberg__', False):
            return

        methods = get_public_methods(instance)
        for name, value in methods:
            signature = inspect.signature(value)

            dep_params = MappingProxyType({
                param_name: param
                for param_name, param in signature.parameters.items()
                if isinstance(param.default, Dependency)
            })
            if not dep_params:
                continue

            instance_method = getattr(instance, name)
            if asyncio.iscoroutinefunction(instance_method):
                async def wrapped_method(*args, __m=instance_method, __s=signature, __n=name, __d=dep_params, **kwargs):
                    new_kwargs = await self._resolve_kwargs(__s, __n, args, kwargs, __d)
                    return await __m(*args, **new_kwargs)

                setattr(instance, name, wrapped_method)
            else:
                raise NotImplementedError('Synchronous methods with Dependency() defaults are not supported.')

        try:
            setattr(instance, '__dinkleberg__', True)
        except (AttributeError, TypeError):
            # Some objects (like those with __slots__) might not allow new attributes
            pass

    @overload
    def add_singleton[I](self, *, instance: I):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], instance: I):
        ...

    @overload
    def add_singleton[T](self, *, t: type[T]):
        ...

    @overload
    def add_singleton[I](self, *, i: type[I]):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], i: type[I]):
        ...

    @overload
    def add_singleton[I](self, *, callable: Callable[..., I]):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], callable: Callable[..., I]):
        ...

    @overload
    def add_singleton[I](self, *, generator: Callable[..., AsyncGenerator[I]]):
        ...

    @overload
    def add_singleton[T, I](self, *, t: type[T], generator: Callable[..., AsyncGenerator[I]]):
        ...

    def add_singleton[T, I](self, *, t: type[T] = None, i: type[I] = None,
                            generator: Callable[..., AsyncGenerator[I]] = None,
                            callable: Callable[..., I] = None, instance: I = None):
        self._raise_if_closed()
        if self._parent is not None:
            raise RuntimeError(
                'Cannot add singleton to a scoped DependencyConfigurator. Add it to the root DependencyConfigurator.')

        if instance is None:
            self._add('singleton', t=t, i=i, generator=generator, callable=callable)
            return
        elif t is None:
            t = type(instance)

        self._wrap_instance(instance)

        self._singleton_instances[t] = instance

    @overload
    def add_scoped[T](self, *, t: type[T]):
        ...

    @overload
    def add_scoped[I](self, *, i: type[I]):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], i: type[I]):
        ...

    @overload
    def add_scoped[I](self, *, callable: Callable[..., I]):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], callable: Callable[..., I]):
        ...

    @overload
    def add_scoped[I](self, *, generator: Callable[..., AsyncGenerator[I]]):
        ...

    @overload
    def add_scoped[T, I](self, *, t: type[T], generator: Callable[..., AsyncGenerator[I]]):
        ...

    def add_scoped[T, I](self, *, t: type[T] = None, i: type[I] = None,
                         generator: Callable[..., AsyncGenerator[I]] = None, callable: Callable[..., I] = None):
        self._raise_if_closed()
        self._add('scoped', t=t, i=i, generator=generator, callable=callable)

    @overload
    def add_transient[T](self, *, t: type[T]):
        ...

    @overload
    def add_transient[I](self, *, i: type[I]):
        ...

    @overload
    def add_transient[T, I](self, *, t: type[T], i: type[I]):
        ...

    @overload
    def add_transient[I](self, *, callable: Callable[..., I]):
        ...

    @overload
    def add_transient[T, I](self, *, t: type[T], callable: Callable[..., I]):
        ...

    def add_transient[T, I](self, *, t: type[T] = None, i: type[I] = None, callable: Callable[..., I] = None):
        self._raise_if_closed()
        self._add('transient', i=i, t=t, callable=callable)
