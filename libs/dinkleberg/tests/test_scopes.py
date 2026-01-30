import pytest


class TestClass:
    pass


@pytest.mark.asyncio
async def test_resolve_scoped_generator(di):
    close_counter = 0

    async def generator():
        yield TestClass()
        nonlocal close_counter
        close_counter += 1

    di.add_scoped(t=TestClass, generator=generator)

    scope = di.scope()

    instance1 = await scope.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await scope.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is instance2

    await scope.close()

    assert close_counter == 1
