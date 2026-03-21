import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

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


@pytest.fixture
def client(api):
    return TestClient(api)
