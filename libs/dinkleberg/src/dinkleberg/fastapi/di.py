import logging

from fastapi import Depends, HTTPException

from .request_scope import request_scope
from ..dependency_scope import DependencyScope
from ..dependency_resolution_error import DependencyResolutionError

logger = logging.getLogger(__name__)


def di[T](t: type[T], **kwargs) -> T:
    async def dependable(scope: DependencyScope = Depends(request_scope)):
        try:
            return await scope.resolve(t, **kwargs)
        except DependencyResolutionError as e:
            if isinstance(e.original_error, HTTPException):
                raise e.original_error

            logger.exception('Error resolving dependency %s', t)
            raise HTTPException(status_code=500)

    return Depends(dependable)
