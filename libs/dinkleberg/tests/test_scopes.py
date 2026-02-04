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


@pytest.mark.asyncio
async def test_override_singleton_instance(di):
    class Test:
        pass

    test1 = Test()
    di.add_singleton(t=Test, instance=test1)

    scope = di.scope()

    test2 = Test()
    scope.add_singleton(t=Test, instance=test2)

    instance1 = await di.resolve(Test)
    instance2 = await scope.resolve(Test)

    assert instance1 is test1
    assert instance2 is test2
