from fastapi import Request

from ..dependency_configurator import DependencyConfigurator


# TODO support websockets
async def request_scope(request: Request):
    # TODO better error DX if dinkleberg not found
    parent: DependencyConfigurator = request.app.state.dinkleberg
    scope = parent.scope()
    scope.add_singleton(t=Request, instance=request)
    try:
        yield scope
    finally:
        await scope.close()
