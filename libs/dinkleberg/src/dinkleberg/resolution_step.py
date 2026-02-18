from typing import NamedTuple, Callable, Any


class ResolutionStep(NamedTuple):
    t: type | Callable
    kwargs: dict[str, Any]

    def __str__(self):
        name = getattr(self.t, '__name__', str(self.t))
        if not self.kwargs:
            return name
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        return f"{name}({args_str})"
