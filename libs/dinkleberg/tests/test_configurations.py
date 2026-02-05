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


@pytest.mark.asyncio
async def test_configure_with_scoped_registration(di):
    class Service:
        def __init__(self, value: str):
            self.value = value

        def set_value(self, new_value: str):
            self.value = new_value

    di.add_scoped(t=Service, callable=lambda: Service('default'))

    instance1 = await di.resolve(Service)

    scope = di.scope()

    scope.configure(Service, lambda svc: svc.set_value('configured'))

    instance2 = await scope.resolve(Service)

    assert instance1.value == 'default'
    assert instance2.value == 'configured'


@pytest.mark.asyncio
async def test_configure_instance_override(di):
    class Service:
        def __init__(self, value: str):
            self.value = value

        def with_value(self, new_value: str):
            return Service(new_value)

    instance1 = await di.resolve(Service, value='default')

    di.configure(Service, lambda svc: svc.with_value('configured'))

    instance2 = await di.resolve(Service, value='test')

    assert instance1.value == 'default'
    assert instance2.value == 'configured'
