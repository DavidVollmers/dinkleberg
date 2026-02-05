import pytest

from dinkleberg import Dependency


@pytest.mark.asyncio
async def test_generic_provider(di):
    class GenericClass[T]:
        def __init__(self, value: T):
            self.value = value

    di.add_transient(t=GenericClass, callable=lambda value: GenericClass(value))

    str_instance = await di.resolve(GenericClass[str], value='hello')

    assert isinstance(str_instance, GenericClass)
    assert str_instance.value == 'hello'


@pytest.mark.asyncio
async def test_resolve_generic_function(di):
    async def test[T](value: T) -> T:
        return value

    f = await di.resolve(test)

    result = await f('Hello, World!')

    assert result == 'Hello, World!'
