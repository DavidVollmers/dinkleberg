import pytest_asyncio
from dinkleberg import DependencyConfigurator


@pytest_asyncio.fixture
async def di():
    deps = DependencyConfigurator()
    yield deps
    await deps.close()
