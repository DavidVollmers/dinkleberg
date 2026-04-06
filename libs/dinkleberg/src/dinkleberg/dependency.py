class _Dependency:
    def __init__(self, t: type = None, **kwargs):
        self._t = t
        self._kwargs = kwargs


# noinspection PyPep8Naming
def Dependency[T](t: type[T] = None, **kwargs) -> T:
    return _Dependency(t, **kwargs)
