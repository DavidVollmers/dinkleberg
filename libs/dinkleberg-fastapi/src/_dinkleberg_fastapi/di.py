import logging
from typing import TYPE_CHECKING

from fastapi import Depends, Request, HTTPException
from dinkleberg_abc import DependencyScope

if TYPE_CHECKING:
    from dinkleberg import DependencyConfigurator

logger = logging.getLogger(__name__)


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
        from dinkleberg import DependencyResolutionError
        try:
            return await scope.resolve(t, **kwargs)
        except DependencyResolutionError as e:
            if isinstance(e.original_error, HTTPException):
                raise e.original_error

            logger.exception('Error resolving dependency %s', t)
            raise HTTPException(status_code=500)

    return Depends(dependable)
