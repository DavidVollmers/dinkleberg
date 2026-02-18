from abc import ABC, ABCMeta, abstractmethod

import pytest

from dinkleberg import DependencyResolutionError


@pytest.mark.asyncio
async def test_resolve_abc(di):
    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(ABC)

    assert f'Cannot resolve abstract class {ABC} without explicit registration.' in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_abc_class(di):
    class AbstractClass(ABC):
        @abstractmethod
        def method(self):
            pass

    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(AbstractClass)

    assert f'Cannot resolve abstract class {AbstractClass} without explicit registration.' in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_abc_class_without_methods(di):
    class AbstractClass(ABC):
        pass

    instance = await di.resolve(AbstractClass)
    assert isinstance(instance, AbstractClass)


@pytest.mark.asyncio
async def test_resolve_abcmeta_class(di):
    class AbstractMetaClass(metaclass=ABCMeta):
        @abstractmethod
        def method(self):
            pass

    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(AbstractMetaClass)

    assert f'Cannot resolve abstract class {AbstractMetaClass} without explicit registration.' in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_abcmeta_class_without_methods(di):
    class AbstractMetaClass(metaclass=ABCMeta):
        pass

    instance = await di.resolve(AbstractMetaClass)
    assert isinstance(instance, AbstractMetaClass)


@pytest.mark.asyncio
async def test_resolve_by_abstraction(di):
    class A(ABC):
        @abstractmethod
        def do_something(self):
            pass

    class B(A):
        def do_something(self):
            return 'B did something'

    class D:
        def __init__(self, a: A):
            self.a = a

        def perform(self):
            return self.a.do_something()

    di.add_transient(t=A, i=B)

    d = await di.resolve(D)

    assert d.perform() == 'B did something'


@pytest.mark.asyncio
async def test_resolve_by_abstraction_with_factory(di):
    class A(ABC):
        @abstractmethod
        def do_something(self):
            pass

    class B(A):
        def __init__(self, value):
            self.value = value

        def do_something(self):
            return 'B did ' + self.value

    class D:
        def __init__(self, a: A):
            self.a = a

        def perform(self):
            return self.a.do_something()

    di.add_transient(t=B, callable=lambda: B('something'))
    di.add_transient(t=A, i=B)

    d = await di.resolve(D)

    assert d.perform() == 'B did something'
