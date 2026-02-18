from typing import Union

import pytest

from dinkleberg import DependencyResolutionError


class TestClass:
    pass


@pytest.mark.asyncio
async def test_register_generator_as_callable(di):
    async def generator():
        yield TestClass()

    di.add_transient(t=TestClass, callable=generator)

    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(TestClass)

    assert (f'Callable {TestClass} returned a generator. '
            f'This is most likely due to an invalid dependency registration.') in str(exc_info.value)


@pytest.mark.asyncio
async def test_builtin_parameters(di):
    class Service:
        def __init__(self, value: str):
            self.value = value

    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(Service)

    assert 'Service.__init__() missing 1 required positional argument: \'value\'' in str(exc_info.value)


@pytest.mark.asyncio
async def test_used_after_closing(di):
    di.add_singleton(t=int, instance=42)
    await di.close()

    with pytest.raises(RuntimeError, match='DependencyScope is already closed.'):
        await di.resolve(int)

    with pytest.raises(RuntimeError, match='DependencyScope is already closed.'):
        di.add_singleton(t=str, instance='test')


@pytest.mark.asyncio
async def test_resolve_union(di):
    class Test1:
        pass

    class Test2:
        pass

    union = Union[Test1, Test2]

    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(union)

    assert f'Cannot resolve built-in type {union} without explicit registration.' in str(exc_info.value)
