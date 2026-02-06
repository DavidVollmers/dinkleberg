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


@pytest.mark.asyncio
async def test_resolve_function_with_kwargs(di):
    class Test:
        def __init__(self, name):
            self._name = name

        def get_message(self):
            return f'Hello, {self._name}!'

    async def test(t: Test = Dependency(), **kwargs):
        return t.get_message()

    f = await di.resolve(test)

    result = await f(name='Dinkleberg')

    assert result == 'Hello, Dinkleberg!'


@pytest.mark.asyncio
async def test_resolve_function_dep_with_kwargs(di):
    class Test:
        def __init__(self, name):
            self._name = name

        def get_message(self):
            return f'Hello, {self._name}!'

    async def test(t: Test = Dependency(name='Dinkleberg')):
        return t.get_message()

    f = await di.resolve(test)

    result = await f()

    assert result == 'Hello, Dinkleberg!'
