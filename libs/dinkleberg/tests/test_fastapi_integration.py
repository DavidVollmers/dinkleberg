import pytest
from fastapi import APIRouter, HTTPException

from dinkleberg.fastapi import di as fastapi_di


@pytest.mark.asyncio
async def test_resolve(di, api, client):
    class TestDependency:
        def __init__(self, value: str):
            self.value = value

    singleton_instance = TestDependency('Hello, Dinkleberg!')
    di.add_singleton(t=TestDependency, instance=singleton_instance)

    router = APIRouter()

    @router.get('/test')
    async def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return {'value': dep.value}

    api.include_router(router)

    response = await client.get('/test')
    assert response.status_code == 200
    assert response.json() == {'value': 'Hello, Dinkleberg!'}


@pytest.mark.asyncio
async def test_error(di, api, client):
    class TestDependency:
        pass

    def test_callable():
        raise ValueError('Something went wrong')

    di.add_singleton(t=TestDependency, callable=test_callable)

    router = APIRouter()

    @router.get('/test')
    async def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return 'This should never be returned'

    api.include_router(router)

    response = await client.get('/test')
    assert response.status_code == 500
    assert response.json() == {'detail': 'Internal Server Error'}


@pytest.mark.asyncio
async def test_http_exception(di, api, client):
    class TestDependency:
        pass

    def test_callable():
        raise HTTPException(status_code=400, detail='Custom error message')

    di.add_singleton(t=TestDependency, callable=test_callable)

    router = APIRouter()

    @router.get('/test')
    async def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return 'This should never be returned'

    api.include_router(router)

    response = await client.get('/test')
    assert response.status_code == 400
    assert response.json() == {'detail': 'Custom error message'}
