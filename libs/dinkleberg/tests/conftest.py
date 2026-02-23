import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from dinkleberg import DependencyConfigurator


@pytest_asyncio.fixture
async def di():
    deps = DependencyConfigurator()
    yield deps
    await deps.close()


@pytest.fixture
def api(di):
    app = FastAPI()
    app.state.dinkleberg = di
    return app


@pytest_asyncio.fixture
async def client(api):
    async with AsyncClient(transport=ASGITransport(app=api), base_url='http://test') as client:
        yield client
