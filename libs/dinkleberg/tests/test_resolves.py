import pytest

from dinkleberg import DependencyConfigurator
from dinkleberg_abc import DependencyScope


class TestClass:
    pass


@pytest.mark.asyncio
async def test_resolve_unregistered(di):
    instance1 = await di.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await di.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is not instance2


@pytest.mark.asyncio
async def test_resolve_transient_callable(di):
    def callable():
        return TestClass()

    di.add_transient(t=TestClass, callable=callable)

    instance1 = await di.resolve(TestClass)
    assert isinstance(instance1, TestClass)

    instance2 = await di.resolve(TestClass)
    assert isinstance(instance2, TestClass)

    assert instance1 is not instance2


@pytest.mark.asyncio
async def test_transient_nested_dependencies(di):
    class Repository:
        # noinspection PyMethodMayBeStatic
        def get_data(self):
            return 'data'

    class Service:
        def __init__(self, repo: Repository):
            self.repo = repo

        def run(self):
            return self.repo.get_data()

    svc = await di.resolve(Service)

    assert svc.run() == 'data'


@pytest.mark.asyncio
async def test_resolve_container(di):
    di1 = await di.resolve(DependencyConfigurator)
    di2 = await di.resolve(DependencyScope)

    assert di is di1
    assert di1 is di2
