import asyncio

import pytest


@pytest.mark.asyncio
async def test_async_callable(di):
    class Test:
        pass

    async def async_callable():
        await asyncio.sleep(0.0001)
        return Test()

    di.add_transient(t=Test, callable=async_callable)

    result = await di.resolve(Test)
    assert isinstance(result, Test)
