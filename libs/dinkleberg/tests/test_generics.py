import pytest


@pytest.mark.asyncio
async def test_resolve_generic_by_callable(di):
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


@pytest.mark.asyncio
async def test_resolve_generic_class_with_type_param(di):
    class Test[T]:
        def __init__(self, t: type[T]):
            self.t = t

    di.add_transient(t=Test)

    instance = await di.resolve(Test[str])

    assert isinstance(instance, Test)
    assert instance.t == str


@pytest.mark.asyncio
async def test_resolve_generic_class_with_callable(di):
    class Test[T]:
        def __init__(self, t: type[T], value: str):
            self.t = t
            self.value = value

    def callable[T](t: type[T]) -> Test[T]:
        return Test(t, value='test')

    di.add_transient(t=Test, callable=callable)

    instance = await di.resolve(Test[str])

    assert isinstance(instance, Test)
    assert instance.t == str
    assert instance.value == 'test'
