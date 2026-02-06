from typing import TYPE_CHECKING

from fastapi import Depends, Request
from dinkleberg_abc import DependencyScope

if TYPE_CHECKING:
    from dinkleberg import DependencyConfigurator


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


def di[T](t: type[T], **kwargs) -> T:
    async def dependable(scope: DependencyScope = Depends(request_scope)):
        return await scope.resolve(t, **kwargs)

    return Depends(dependable)
