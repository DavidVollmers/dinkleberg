from typing import Optional

import pytest
from fastapi import APIRouter, HTTPException, Request
from fastapi.websockets import WebSocket

from dinkleberg.fastapi import di as fastapi_di


def test_resolve(di, api, client):
    class TestDependency:
        def __init__(self, value: str):
            self.value = value

    singleton_instance = TestDependency('Hello, Dinkleberg!')
    di.add_singleton(t=TestDependency, instance=singleton_instance)

    router = APIRouter()

    @router.get('/test')
    def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return {'value': dep.value}

    api.include_router(router)

    response = client.get('/test')
    assert response.status_code == 200
    assert response.json() == {'value': 'Hello, Dinkleberg!'}


def test_error(di, api, client):
    class TestDependency:
        pass

    def test_callable():
        raise ValueError('Something went wrong')

    di.add_singleton(t=TestDependency, callable=test_callable)

    router = APIRouter()

    @router.get('/test')
    def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return 'This should never be returned'

    api.include_router(router)

    response = client.get('/test')
    assert response.status_code == 500
    assert response.json() == {'detail': 'Internal Server Error'}


def test_http_exception(di, api, client):
    class TestDependency:
        pass

    def test_callable():
        raise HTTPException(status_code=400, detail='Custom error message')

    di.add_singleton(t=TestDependency, callable=test_callable)

    router = APIRouter()

    @router.get('/test')
    def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return 'This should never be returned'

    api.include_router(router)

    response = client.get('/test')
    assert response.status_code == 400
    assert response.json() == {'detail': 'Custom error message'}


def test_resolve_request_or_websocket(di, api, client):
    class TestDependency:
        def __init__(self, request: Optional[Request], websocket: Optional[WebSocket]):
            self.value = 'request' if request is not None else 'websocket' if websocket is not None else None

    router = APIRouter()

    @router.get('/test')
    def test_endpoint(dep: TestDependency = fastapi_di(TestDependency)):
        return {'value': dep.value}

    @router.websocket('/ws')
    async def websocket_endpoint(websocket: WebSocket, dep: TestDependency = fastapi_di(TestDependency)):
        await websocket.accept()
        await websocket.send_json({'value': dep.value})
        await websocket.close()

    api.include_router(router)

    response = client.get('/test')
    assert response.status_code == 200
    assert response.json() == {'value': 'request'}

    with client.websocket_connect('/ws') as ws:
        data = ws.receive_json()
        assert data == {'value': 'websocket'}
