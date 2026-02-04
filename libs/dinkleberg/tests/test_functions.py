import pytest

from dinkleberg_abc import Dependency


@pytest.mark.asyncio
async def test_resolve_function(di):
    class Test:
        def get_message(self):
            return 'Hello, World!'

    async def test(t: Test = Dependency()):
        return t.get_message()

    f = await di.resolve(test)

    result = await f()

    assert result == 'Hello, World!'
