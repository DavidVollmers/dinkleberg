import asyncio

from fastapi import Request
from fastapi.websockets import WebSocket

from ..dependency_configurator import DependencyConfigurator

_dinkleberg_cleanup_tasks = set()


async def request_scope(request: Request = None, websocket: WebSocket = None):
    state = request.app.state if request is not None else websocket.app.state
    if not hasattr(state, 'dinkleberg'):
        raise RuntimeError(
            'Dinkleberg dependency configurator not found in app state. Make sure to set it up correctly.')

    parent: DependencyConfigurator = state.dinkleberg
    scope = parent.scope()

    if request is not None:
        scope.add_singleton(t=Request, instance=request)
    if websocket is not None:
        scope.add_singleton(t=WebSocket, instance=websocket)

    try:
        yield scope
    finally:
        task = asyncio.create_task(scope.close())
        _dinkleberg_cleanup_tasks.add(task)
        task.add_done_callback(_dinkleberg_cleanup_tasks.discard)
