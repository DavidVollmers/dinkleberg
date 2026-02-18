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


@pytest.mark.asyncio
async def test_deep_resolution_error_trace(di):
    # 1. Setup a chain: Root -> Middle -> Leaf (fails)
    class LeafService:
        def __init__(self):
            raise ValueError("Something went wrong in the leaf!")

    class MiddleService:
        def __init__(self, leaf: LeafService):
            self.leaf = leaf

    class RootService:
        def __init__(self, middle: MiddleService):
            self.middle = middle

    # 2. Register them
    di.add_transient(t=LeafService)
    di.add_transient(t=MiddleService)
    di.add_transient(t=RootService)

    # 3. Resolve and catch
    with pytest.raises(DependencyResolutionError) as exc_info:
        await di.resolve(RootService)

    error_str = str(exc_info.value)

    # 4. Assert the path is visible
    assert "RootService" in error_str
    assert "MiddleService" in error_str
    assert "LeafService" in error_str

    # 5. Assert the visual arrow structure exists
    assert "RootService -> \n  MiddleService -> \n  LeafService" in error_str

    # 6. Assert the original error is preserved
    assert "ValueError: Something went wrong in the leaf!" in error_str


@pytest.mark.asyncio
async def test_circular_dependency_detection(di):
    class Chicken:
        def __init__(self, egg: 'Egg'):
            self.egg = egg

    class Egg:  # Redefine to break circular import in pure python for test simplicity
        def __init__(self, chicken: Chicken):
            self.chicken = chicken

    def chicken_factory(egg: Egg) -> Chicken:
        return Chicken(egg)

    di.add_transient(t=Chicken, callable=chicken_factory)

    with pytest.raises(RecursionError) as exc_info:
        await di.resolve(Chicken)

    error_str = str(exc_info.value)

    assert "Circular dependency detected" in error_str
    assert "Chicken -> Egg -> Chicken" in error_str
