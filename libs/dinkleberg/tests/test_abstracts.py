from abc import ABC, ABCMeta, abstractmethod

import pytest


@pytest.mark.asyncio
async def test_resolve_abc(di):
    with pytest.raises(ValueError) as exc_info:
        instance = await di.resolve(ABC)
    assert f'Cannot resolve abstract class {ABC} without explicit registration.' in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_abc_class(di):
    class AbstractClass(ABC):
        @abstractmethod
        def method(self):
            pass

    with pytest.raises(ValueError) as exc_info:
        instance = await di.resolve(AbstractClass)
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

    with pytest.raises(ValueError) as exc_info:
        instance = await di.resolve(AbstractMetaClass)
    assert f'Cannot resolve abstract class {AbstractMetaClass} without explicit registration.' in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_abcmeta_class_without_methods(di):
    class AbstractMetaClass(metaclass=ABCMeta):
        pass

    instance = await di.resolve(AbstractMetaClass)
    assert isinstance(instance, AbstractMetaClass)
