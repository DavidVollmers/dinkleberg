from typing import Optional, TypedDict, Callable, AsyncGenerator, Literal, Union

Lifetime = Union[Literal['singleton'], Literal['scoped'], Literal['transient']]


class Descriptor(TypedDict):
    generator: Optional[Callable[..., AsyncGenerator]]
    callable: Optional[Callable]
    lifetime: Lifetime
