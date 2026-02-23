import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from dinkleberg import DependencyConfigurator


@pytest.fixture
def deps():
    return DependencyConfigurator()


@pytest.fixture
def api(deps):
    app = FastAPI()
    app.state.dinkleberg = deps
    return app


@pytest_asyncio.fixture
async def client(api):
    async with AsyncClient(transport=ASGITransport(app=api), base_url='http://test') as client:
        yield client
