from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _dinkleberg_fastapi import di

try:
    from _dinkleberg_fastapi import di

    __all__ = ['di']
except ImportError:
    raise ImportError(
        "dinkleberg-fastapi is not installed. Please install it with 'pip install dinkleberg[fastapi]' to use FastAPI integration."
    )
