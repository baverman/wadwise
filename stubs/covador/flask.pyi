from typing import Any, Callable, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec('P')
R = TypeVar('R')
F = Callable[P, R]

def query_string(*args: Any, **kwargs: Any) -> Callable[[F[P, R]], F[P, R]]: ...
def form(*args: Any, **kwargs: Any) -> Callable[[F[P, R]], F[P, R]]: ...
