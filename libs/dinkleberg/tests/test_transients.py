import pytest


class TestClass:
    pass


@pytest.mark.asyncio
async def test_resolve_class(di):
    instance1 = await di.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await di.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is not instance2
