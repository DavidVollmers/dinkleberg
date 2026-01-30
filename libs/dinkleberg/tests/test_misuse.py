import pytest


class TestClass:
    pass


@pytest.mark.asyncio
async def test_register_generator_as_callable(di):
    async def generator():
        yield TestClass()

    di.add_transient(t=TestClass, callable=generator)

    with pytest.raises(RuntimeError) as exc_info:
        instance = await di.resolve(TestClass)

    assert f'Callable {TestClass} returned a generator. This is most likely due to an invalid dependency registration.' in str(
        exc_info.value)
