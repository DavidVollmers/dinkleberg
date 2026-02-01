import pytest


class TestClass:
    pass


@pytest.mark.asyncio
async def test_register_generator_as_callable(di):
    async def generator():
        yield TestClass()

    di.add_transient(t=TestClass, callable=generator)

    with pytest.raises(RuntimeError) as exc_info:
        await di.resolve(TestClass)

    assert f'Callable {TestClass} returned a generator. This is most likely due to an invalid dependency registration.' in str(
        exc_info.value)


@pytest.mark.asyncio
async def test_builtin_parameters(di):
    class Service:
        def __init__(self, value: str):
            self.value = value

    with pytest.raises(TypeError) as exc_info:
        await di.resolve(Service)

    assert f'Service.__init__() missing 1 required positional argument: \'value\'' in str(exc_info.value)
