import pytest


@pytest.mark.asyncio
async def test_configure(di):
    class Service:
        def __init__(self, value: str):
            self.value = value

        def set_value(self, new_value: str):
            self.value = new_value

    instance1 = await di.resolve(Service, value='default')

    di.configure(Service, lambda svc: svc.set_value('configured'))

    instance2 = await di.resolve(Service, value='unconfigured')

    assert instance1.value == 'default'
    assert instance2.value == 'configured'
