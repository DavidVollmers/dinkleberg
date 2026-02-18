from .resolution_step import ResolutionStep


class DependencyResolutionError(Exception):
    def __init__(self, chain: tuple[ResolutionStep, ...], message: str = None, original_error: Exception = None):
        self._chain = chain
        self._message = message
        self._original_error = original_error
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        path = ' -> \n  '.join(str(step) for step in self._chain)

        message = f'\n\nDependency Resolution Failed:'
        if self._message:
            message += f' {self._message}'
        if self._chain and len(self._chain) > 1:
            message += f'\n  Trace:\n  {path}\n'
        if self._original_error:
            message += f'  {type(self._original_error).__name__}: {str(self._original_error)}\n'

        return message
