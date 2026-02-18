from .resolution_step import ResolutionStep


class DependencyResolutionException(Exception):
    def __init__(self, chain: tuple[ResolutionStep, ...], original_error: Exception):
        self._chain = chain
        self._original_error = original_error
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        path = ' -> \n  '.join(str(step) for step in self._chain)

        return (
            f'\n\nDependency Resolution Failed:\n'
            f'  Trace:\n  {path}\n'
            f'  Error: {type(self._original_error).__name__}: {str(self._original_error)}\n'
        )
