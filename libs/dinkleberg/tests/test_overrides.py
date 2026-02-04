import pytest


@pytest.mark.asyncio
async def test_override_singleton_instance(di):
    class Test:
        pass

    test1 = Test()
    di.add_singleton(t=Test, instance=test1)

    instance1 = await di.resolve(Test)

    test2 = Test()
    di.add_singleton(t=Test, instance=test2, override=True)

    instance2 = await di.resolve(Test)

    assert instance1 is test1
    assert instance2 is test2
