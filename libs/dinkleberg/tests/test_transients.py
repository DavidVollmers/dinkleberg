import pytest


class TestClass:
    pass


@pytest.mark.asyncio
async def test_resolve_unregistered(di):
    instance1 = await di.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await di.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is not instance2


@pytest.mark.asyncio
async def test_resolve_transient_callable(di):
    def callable():
        return TestClass()

    di.add_transient(t=TestClass, callable=callable)

    instance1 = await di.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await di.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is not instance2
